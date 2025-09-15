"""
Analyzes conversation results and measures intervention effectiveness.
"""
import json
import numpy as np
import pandas as pd
from typing import Dict, List, Tuple
from pathlib import Path
from datetime import datetime


class MetricsAnalyzer:
    """Analyzes conversations to measure intervention effectiveness."""

    def __init__(self, results_dir: str = "simulation/results"):
        self.results_dir = Path(results_dir)
        self.conversations_dir = self.results_dir / "conversations"

    def analyze_all_conversations(self) -> pd.DataFrame:
        """Load and analyze all conversations."""

        all_results = []

        # Load all conversation files
        for conv_file in self.conversations_dir.glob("*.json"):
            with open(conv_file, 'r', encoding='utf-8') as f:
                conv_data = json.load(f)

            # Analyze individual conversation
            metrics = self.analyze_conversation(conv_data)
            all_results.append(metrics)

        # Create DataFrame
        df = pd.DataFrame(all_results)

        # Add summary statistics
        if not df.empty:
            self._add_summary_stats(df)

        return df

    def analyze_conversation(self, conv_data: Dict) -> Dict:
        """Analyze a single conversation."""

        profile = conv_data['profile_data']
        conversation = conv_data['conversation']
        metadata = conv_data.get('metadata', {})

        # Extract basic info
        metrics = {
            'profile_id': conv_data.get('profile_id', 'unknown'),
            'intervention': conv_data.get('intervention', 'unknown'),
            'political_stance': profile.get('basic_info', {}).get('political_stance', 0),
            'age': profile.get('basic_info', {}).get('age', 0),
            'gender': profile.get('basic_info', {}).get('gender', ''),
            'military_service': profile.get('political_behavior', {}).get('military_service_recent', ''),

            # War positions
            'war_priority': profile.get('war_position', {}).get('war_priority_pre', ''),
            'israel_action': profile.get('war_position', {}).get('israel_action_pre', ''),

            # Conversation metrics
            'total_messages': len(conversation),
            'user_messages': len([m for m in conversation if m['role'] == 'user']),
            'agent_messages': len([m for m in conversation if m['role'] == 'assistant']),
            'ending_reason': metadata.get('ending_reason', 'unknown'),

            # Content analysis
            'agreement_signals': self._count_agreement_signals(conversation),
            'disagreement_signals': self._count_disagreement_signals(conversation),
            'empathy_expressions': self._count_empathy_expressions(conversation),
            'shared_identity_refs': self._count_shared_identity_references(conversation),
            'emotion_level': self._measure_emotion_level(conversation),

            # Conversation quality
            'avg_message_length': self._calculate_avg_message_length(conversation),
            'back_and_forth_ratio': self._calculate_back_and_forth_ratio(conversation),
            'topic_consistency': self._measure_topic_consistency(conversation),
        }

        return metrics

    def _count_agreement_signals(self, conversation: List[Dict]) -> int:
        """Count agreement signals in conversation."""
        agreement_phrases = [
            "אתה צודק", "את צודקת", "אני מסכים", "אני מסכימה",
            "נכון", "יש בזה משהו", "לא חשבתי על זה",
            "זה נכון", "אתה לא טועה", "יש לך נקודה"
        ]

        count = 0
        for msg in conversation:
            content = msg['content']
            for phrase in agreement_phrases:
                if phrase in content:
                    count += 1
        return count

    def _count_disagreement_signals(self, conversation: List[Dict]) -> int:
        """Count disagreement signals in conversation."""
        disagreement_phrases = [
            "לא מסכים", "לא נכון", "אתה טועה", "את טועה",
            "זה לא מדויק", "אני לא מקבל", "אבל", "לעומת זאת",
            "בניגוד למה ש", "זה שטויות"
        ]

        count = 0
        for msg in conversation:
            content = msg['content']
            for phrase in disagreement_phrases:
                if phrase in content:
                    count += 1
        return count

    def _count_empathy_expressions(self, conversation: List[Dict]) -> int:
        """Count empathy expressions in conversation."""
        empathy_phrases = [
            "אני מבין", "אני מבינה", "אני יכול להבין",
            "זה מובן", "אני מרגיש", "אני מרגישה",
            "קשה לי עם", "אני מזדהה", "אני שומע אותך"
        ]

        count = 0
        for msg in conversation:
            content = msg['content']
            for phrase in empathy_phrases:
                if phrase in content:
                    count += 1
        return count

    def _count_shared_identity_references(self, conversation: List[Dict]) -> int:
        """Count references to shared Israeli identity."""
        shared_phrases = [
            "כולנו", "אנחנו כעם", "החברה שלנו",
            "המדינה שלנו", "הילדים שלנו", "העתיד שלנו",
            "ביחד", "כישראלים", "המשפחה הישראלית"
        ]

        count = 0
        for msg in conversation:
            content = msg['content']
            for phrase in shared_phrases:
                if phrase in content:
                    count += 1
        return count

    def _measure_emotion_level(self, conversation: List[Dict]) -> float:
        """Measure emotional intensity of conversation (0-1 scale)."""
        emotion_markers = [
            "!", "!!", "!!!", "...", "????",
            "מאוד", "ממש", "נורא", "איום", "נפלא",
            "כואב", "קשה", "מפחיד", "מדהים", "מזעזע"
        ]

        total_markers = 0
        for msg in conversation:
            content = msg['content']
            for marker in emotion_markers:
                total_markers += content.count(marker)

        # Normalize by message count
        return min(1.0, total_markers / max(len(conversation), 1) / 2)

    def _calculate_avg_message_length(self, conversation: List[Dict]) -> float:
        """Calculate average message length in characters."""
        if not conversation:
            return 0

        total_length = sum(len(msg['content']) for msg in conversation)
        return total_length / len(conversation)

    def _calculate_back_and_forth_ratio(self, conversation: List[Dict]) -> float:
        """Calculate ratio of back-and-forth exchanges."""
        if len(conversation) < 2:
            return 0

        transitions = 0
        for i in range(1, len(conversation)):
            if conversation[i]['role'] != conversation[i - 1]['role']:
                transitions += 1

        return transitions / (len(conversation) - 1)

    def _measure_topic_consistency(self, conversation: List[Dict]) -> float:
        """Measure how consistently the conversation stays on topic (war/Gaza)."""
        topic_keywords = [
            "עזה", "מלחמה", "חטופים", "חמאס",
            "צבא", "לחימה", "הפסקת אש", "עסקה",
            "ביטחון", "חיילים", "אוקטובר"
        ]

        on_topic_messages = 0
        for msg in conversation:
            content = msg['content']
            if any(keyword in content for keyword in topic_keywords):
                on_topic_messages += 1

        return on_topic_messages / max(len(conversation), 1)

    def _add_summary_stats(self, df: pd.DataFrame) -> None:
        """Add summary statistics to DataFrame."""

        # Group by intervention
        print("\n" + "=" * 50)
        print("SUMMARY BY INTERVENTION")
        print("=" * 50)

        for intervention in df['intervention'].unique():
            intervention_df = df[df['intervention'] == intervention]

            print(f"\n{intervention.upper()}:")
            print(f"  Total conversations: {len(intervention_df)}")
            print(f"  Avg messages: {intervention_df['total_messages'].mean():.1f}")
            print(f"  Avg agreement signals: {intervention_df['agreement_signals'].mean():.2f}")
            print(f"  Avg empathy expressions: {intervention_df['empathy_expressions'].mean():.2f}")
            print(f"  Avg emotion level: {intervention_df['emotion_level'].mean():.3f}")

            if intervention == "shared_identity":
                print(f"  Avg shared identity refs: {intervention_df['shared_identity_refs'].mean():.2f}")

    def generate_report(self, output_file: str = None) -> None:
        """Generate comprehensive analysis report."""

        # Analyze all conversations
        df = self.analyze_all_conversations()

        if df.empty:
            print("No conversations found to analyze")
            return

        # Save to CSV if requested
        if output_file:
            df.to_csv(output_file, index=False, encoding='utf-8')
            print(f"\nAnalysis saved to {output_file}")

        # Print detailed report
        print("\n" + "=" * 60)
        print("DETAILED ANALYSIS REPORT")
        print("=" * 60)

        print(f"\nTotal conversations analyzed: {len(df)}")

        # By political stance
        print("\nBy Political Stance:")
        for stance in sorted(df['political_stance'].unique()):
            stance_df = df[df['political_stance'] == stance]
            stance_label = ["", "Left", "Center-Left", "Center", "Center-Right", "Right"][stance]
            print(f"  {stance_label}: {len(stance_df)} conversations")

        # Effectiveness indicators
        print("\n" + "-" * 50)
        print("EFFECTIVENESS INDICATORS")
        print("-" * 50)

        # Calculate effectiveness score
        for intervention in df['intervention'].unique():
            int_df = df[df['intervention'] == intervention]

            # Simple effectiveness score
            effectiveness = (
                                    int_df['agreement_signals'].mean() * 2 +
                                    int_df['empathy_expressions'].mean() * 3 -
                                    int_df['disagreement_signals'].mean() * 1
                            ) / int_df['total_messages'].mean()

            print(f"\n{intervention}:")
            print(f"  Effectiveness score: {effectiveness:.3f}")
            print(f"  Topic consistency: {int_df['topic_consistency'].mean():.2%}")
            print(f"  Natural endings: {(int_df['ending_reason'] != 'hard_limit').mean():.2%}")