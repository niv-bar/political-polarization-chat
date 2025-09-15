"""
Simulates conversations between fake users and AI agents with different interventions.
"""
import random
import json
import time
import re
from typing import Dict, List, Tuple, Optional
from datetime import datetime
from pathlib import Path

from google import genai as google_genai
from google.genai import types

from .interventions import INTERVENTIONS, AGENT_OPENINGS, ENDING_PROGRESSIONS
from .fake_profiles.profile_loader import ProfileLoader


class ConversationEndingManager:
    """Manages natural conversation endings."""

    def __init__(self):
        self.ending_phases = {
            "active": (0, 16),
            "pre_closure": (16, 18),
            "soft_closure": (18, 20),
            "closure": (20, 22),
            "final": (22, 24)
        }

    def get_phase(self, message_count: int) -> str:
        """Get current conversation phase based on message count."""
        for phase, (min_msgs, max_msgs) in self.ending_phases.items():
            if min_msgs <= message_count < max_msgs:
                return phase
        return "final"

    def should_end(self, message_count: int, last_messages: List[Dict]) -> Tuple[bool, str]:
        """Determine if conversation should end."""
        # Hard limit
        if message_count >= 24:
            return True, "hard_limit"

        # Check for natural ending after minimum
        if message_count >= 18:
            # Check last message for ending signals
            if last_messages:
                last_msg = last_messages[-1]['content']
                ending_phrases = [
                    "תודה על השיחה",
                    "היה מעניין",
                    "נחמד שדיברנו",
                    "אני צריך ללכת",
                    "בוא נסיים",
                    "נסכים שלא נסכים"
                ]
                if any(phrase in last_msg for phrase in ending_phrases):
                    return True, "natural_ending"

        # Soft ending probability increases after 20 messages
        if message_count >= 20:
            if random.random() < 0.3:
                return True, "soft_ending"

        return False, None


class ConversationSimulator:
    def __init__(self, gemini_api_key: str):
        self.client = google_genai.Client(api_key=gemini_api_key)
        self.profile_loader = ProfileLoader()
        self.ending_manager = ConversationEndingManager()
        self.last_request_time = 0
        self.min_request_interval = 10  # 6 seconds between requests for safety (10 per minute)

    def _wait_for_rate_limit(self):
        """Ensure minimum time between requests."""
        elapsed = time.time() - self.last_request_time
        if elapsed < self.min_request_interval:
            wait_time = self.min_request_interval - elapsed
            print(f"  Waiting {wait_time:.1f}s to avoid rate limit...")
            time.sleep(wait_time)
        self.last_request_time = time.time()

    def _extract_retry_delay(self, error_str: str) -> int:
        """Extract retry delay from error message."""
        match = re.search(r"'retryDelay':\s*'(\d+)s'", str(error_str))
        if match:
            return int(match.group(1))
        return 60  # Default to 60 seconds

    def _generate_agent_response(self,
                                 conversation: List[Dict],
                                 intervention_prompt: str,
                                 profile_data: Dict,
                                 phase: str,
                                 max_retries: int = 3) -> str:
        """Generate agent response with retry logic."""

        # Get user stance for better targeting
        from .interventions import get_user_stance
        stance = get_user_stance(profile_data)

        for attempt in range(max_retries):
            try:
                self._wait_for_rate_limit()

                history = "\n".join([
                    f"{'User' if msg['role'] == 'user' else 'Agent'}: {msg['content']}"
                    for msg in conversation
                ])

                phase_instructions = self._get_phase_instructions(phase)

                prompt = f"""
    {intervention_prompt}

    Current conversation phase: {phase}
    {phase_instructions}

    Conversation so far:
    {history}

    User profile context:
    - Political stance: {'RIGHT' if stance['is_right'] else 'LEFT' if stance['is_left'] else 'CENTER'}
    - Prioritizes: {'Hostages' if stance['prioritizes_hostages'] else 'Security/Hamas elimination' if stance['prioritizes_security'] else 'Unclear'}
    - Prefers: {'Negotiation/Deal' if stance['wants_deal'] else 'Military action' if stance['wants_military'] else 'Unclear'}

    IMPORTANT: You must present the OPPOSITE view from theirs while building bridges.

    Generate the next agent response in Hebrew. Keep it natural and conversational.
    Response should be 2-4 sentences maximum.
    """

                response = self.client.models.generate_content(
                    model="gemini-2.0-flash-exp",
                    contents=prompt,
                    config=types.GenerateContentConfig(
                        temperature=0.8,
                        top_p=0.9,
                        max_output_tokens=300
                    )
                )
                return response.text.strip()

            except Exception as e:
                error_str = str(e)
                print(f"  Attempt {attempt + 1} failed: {error_str[:100]}...")

                if "429" in error_str and "RESOURCE_EXHAUSTED" in error_str:
                    retry_delay = self._extract_retry_delay(error_str)
                    if attempt < max_retries - 1:
                        print(f"  Rate limited. Waiting {retry_delay}s...")
                        time.sleep(retry_delay + 2)  # Add 2s buffer
                        continue

                # For last attempt or non-rate-limit errors
                if attempt == max_retries - 1:
                    # Return a contextual fallback response
                    return self._get_fallback_response(phase, "agent")

        return self._get_fallback_response(phase, "agent")

    def _generate_user_response(self,
                                profile_data: Dict,
                                conversation: List[Dict],
                                phase: str,
                                max_retries: int = 3) -> str:
        """Generate user response with retry logic."""

        style = profile_data.get('conversation_style', {})
        typical_phrases = style.get('typical_phrases', [])

        for attempt in range(max_retries):
            try:
                # Wait before making request
                self._wait_for_rate_limit()

                # Build conversation history
                history = "\n".join([
                    f"{'User' if msg['role'] == 'user' else 'Agent'}: {msg['content']}"
                    for msg in conversation[-4:]
                ])

                prompt = f"""
You are playing the role of an Israeli with these characteristics:
- Age: {profile_data.get('basic_info', {}).get('age')}
- Gender: {profile_data.get('basic_info', {}).get('gender')}
- Political stance: {profile_data.get('basic_info', {}).get('political_stance')} (1=left, 5=right)
- War priority: {profile_data.get('war_position', {}).get('war_priority_pre')}
- Preferred action: {profile_data.get('war_position', {}).get('israel_action_pre')}

Your typical phrases: {typical_phrases}

Recent conversation:
{history}

Current phase: {phase}

Generate your next response in Hebrew. Be consistent with your political position.
Keep it natural and emotional. 2-3 sentences maximum.
{'If the conversation is winding down, you can acknowledge this naturally.' if phase in ['soft_closure', 'closure'] else ''}
"""

                response = self.client.models.generate_content(
                    model="gemini-2.0-flash-exp",
                    contents=prompt,
                    config=types.GenerateContentConfig(
                        temperature=0.85,
                        top_p=0.9,
                        max_output_tokens=250
                    )
                )
                return response.text.strip()

            except Exception as e:
                error_str = str(e)
                print(f"  User attempt {attempt + 1} failed: {error_str[:100]}...")

                if "429" in error_str and "RESOURCE_EXHAUSTED" in error_str:
                    retry_delay = self._extract_retry_delay(error_str)
                    if attempt < max_retries - 1:
                        print(f"  Rate limited. Waiting {retry_delay}s...")
                        time.sleep(retry_delay + 2)
                        continue

                # Use typical phrase as fallback
                if attempt == max_retries - 1:
                    if typical_phrases:
                        return random.choice(typical_phrases)
                    return self._get_fallback_response(phase, "user")

        return self._get_fallback_response(phase, "user")

    def _get_fallback_response(self, phase: str, role: str) -> str:
        """Get contextual fallback response when API fails."""

        if role == "agent":
            fallbacks = {
                "active": "אני מבין את העמדה שלך. זה באמת מצב מורכב.",
                "pre_closure": "נראה שאנחנו נוגעים בנקודות חשובות פה.",
                "soft_closure": "למרות הבדלי הדעות, אני מעריך את הפתיחות שלך.",
                "closure": "תודה על השיחה הכנה. זה חשוב שאנחנו מדברים.",
                "final": "היה חשוב לשמוע את הזווית שלך. תודה."
            }
        else:  # user
            fallbacks = {
                "active": "זה מסובך. קשה לי עם כל המצב.",
                "pre_closure": "כן, יש הרבה מה לחשוב עליו.",
                "soft_closure": "אני מבין מאיפה אתה בא.",
                "closure": "תודה על השיחה.",
                "final": "היה מעניין."
            }

        return fallbacks.get(phase, "נכון." if role == "user" else "אני מבין.")

    def simulate_conversation(self,
                              profile_data: Dict,
                              intervention_type: str,
                              max_messages: int = 24) -> Dict:
        """Simulate a complete conversation."""

        # Initialize conversation
        conversation = []
        start_time = datetime.now()

        # Get intervention prompt
        intervention_prompt = INTERVENTIONS[intervention_type]

        # Agent opens the conversation
        opening = random.choice(AGENT_OPENINGS)
        conversation.append({
            "role": "assistant",
            "content": opening,
            "timestamp": datetime.now().isoformat()
        })

        # Get user's opening response from profile
        user_opening = self._generate_user_opening(profile_data)
        conversation.append({
            "role": "user",
            "content": user_opening,
            "timestamp": datetime.now().isoformat()
        })

        # Continue conversation
        while len(conversation) < max_messages:
            phase = self.ending_manager.get_phase(len(conversation))

            # Generate agent response
            agent_response = self._generate_agent_response(
                conversation,
                intervention_prompt,
                profile_data,
                phase
            )

            conversation.append({
                "role": "assistant",
                "content": agent_response,
                "timestamp": datetime.now().isoformat()
            })

            # Check if should end
            should_end, reason = self.ending_manager.should_end(
                len(conversation),
                conversation[-2:]
            )

            if should_end:
                # Add final user acknowledgment if ending naturally
                if reason != "hard_limit":
                    final_user = self._generate_user_closing(profile_data, conversation)
                    conversation.append({
                        "role": "user",
                        "content": final_user,
                        "timestamp": datetime.now().isoformat()
                    })
                break

            # Generate user response
            user_response = self._generate_user_response(
                profile_data,
                conversation,
                phase
            )

            conversation.append({
                "role": "user",
                "content": user_response,
                "timestamp": datetime.now().isoformat()
            })

        # Return complete conversation data
        return {
            "profile_id": profile_data.get('profile_id', 'unknown'),
            "intervention": intervention_type,
            "conversation": conversation,
            "metadata": {
                "start_time": start_time.isoformat(),
                "end_time": datetime.now().isoformat(),
                "total_messages": len(conversation),
                "ending_reason": reason if 'reason' in locals() else "max_messages"
            },
            "profile_data": profile_data
        }

    def _generate_user_opening(self, profile_data: Dict) -> str:
        """Generate user's opening response based on profile."""
        style = profile_data.get('conversation_style', {})
        return style.get('opening_response', "קשה לי עם כל המצב הזה")

    def _generate_user_closing(self, profile_data: Dict, conversation: List[Dict]) -> str:
        """Generate user's closing response."""
        closings = [
            "תודה על השיחה",
            "היה מעניין לשמוע אותך",
            "נתת לי על מה לחשוב",
            "טוב, נחמד שדיברנו",
            "אני צריך לעכל את זה"
        ]
        return random.choice(closings)

    def _get_phase_instructions(self, phase: str) -> str:
        """Get phase-specific instructions for agent."""
        instructions = {
            "active": "Continue the conversation normally. Focus on understanding their position.",
            "pre_closure": "Start summarizing key points naturally. Don't end abruptly.",
            "soft_closure": "Begin wrapping up by highlighting areas of agreement.",
            "closure": "Provide a thoughtful closing that acknowledges both perspectives.",
            "final": "End gracefully with appreciation for the dialogue."
        }
        return instructions.get(phase, "")

    def save_conversation(self, conversation_data: Dict, output_dir: str = "simulation/results"):
        """Save conversation to local file."""
        output_path = Path(output_dir) / "conversations"
        output_path.mkdir(parents=True, exist_ok=True)

        # Generate filename
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        profile_id = conversation_data['profile_id']
        intervention = conversation_data['intervention']
        filename = f"{timestamp}_{profile_id}_{intervention}.json"

        # Save to file
        file_path = output_path / filename
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(conversation_data, f, ensure_ascii=False, indent=2)

        print(f"Saved conversation to {file_path}")
        return file_path