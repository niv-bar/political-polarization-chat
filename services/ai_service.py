import streamlit as st
from google import genai as google_genai
from google.genai import types
from typing import Optional, Generator
from models import UserProfile

class AIService:
    """Handles AI interactions with optimized streaming."""

    def __init__(self, api_key: str):
        self.api_key = api_key
        self._client = None
        self._initialize_client()

    def _initialize_client(self) -> None:
        """Initialize Gemini client with optimized settings."""
        try:
            self._client = google_genai.Client(api_key=self.api_key)
        except Exception as e:
            st.error(f"❌ Failed to initialize Gemini client: {str(e)}")
            self._client = None

    def generate_response_stream(self, prompt: str, user_profile: Optional[UserProfile] = None,
                                 chat_context: str = "") -> Generator[str, None, None]:
        """Generate optimized streaming response with latest model."""
        if not self._client:
            yield "❌ שגיאה: הלקוח לא מוכן"
            return

        try:
            enhanced_prompt = self._build_prompt(prompt, user_profile, chat_context)

            # Optimized configuration for fastest response
            config = types.GenerateContentConfig(
                tools=[types.Tool(google_search=types.GoogleSearch())],
                temperature=1,
                top_p=0.8,
                top_k=30,
                max_output_tokens=2000,
                candidate_count=1,
                system_instruction=self._build_system_instruction(user_profile)
            )

            # Use latest fastest model
            response_stream = self._client.models.generate_content_stream(
                model="gemini-2.0-flash-exp",  # Latest and fastest model
                contents=enhanced_prompt,
                config=config,
            )

            # Yield chunks immediately
            for chunk in response_stream:
                if hasattr(chunk, 'text') and chunk.text:
                    yield chunk.text

        except Exception as e:
            yield f"❌ שגיאה ב-Gemini: {str(e)}"

    def _build_system_instruction(self, user_profile: Optional[UserProfile]) -> str:
        """Build system instruction with user context."""
        instruction = """אתה עוזר AI חכם ומנומס שמתמחה בנושאים פוליטיים ישראליים. 
    השב תמיד בעברית. השתמש בחיפוש באינטרנט למידע עדכני כשנדרש.
    היה אובייקטיבי ומאוזן, הצג נקודות מבט שונות בנושאים מורכבים."""

        if user_profile:
            instruction += f"""

    מידע על המשתמש:
    - גיל: {user_profile.age}, אזור: {user_profile.region}, השכלה: {user_profile.education}
    - עמדה פוליטית: {user_profile.political_stance}/10 (1=שמאל, 10=ימין)
    - רמת דתיות: {user_profile.religiosity}/10
    - השתתפות בהפגנות: {user_profile.protest_participation}
    - תדירות הצבעה: {user_profile.voting_frequency}
    - דיונים פוליטיים: {user_profile.political_discussions}
    - אמון במערכת: {user_profile.trust_political_system}/10
    - חרדה פוליטית: {user_profile.political_anxiety}/10

    התאם את התגובות לפרופיל המשתמש תוך שמירה על אובייקטיביות."""

        return instruction

    def _build_prompt(self, prompt: str, user_profile: Optional[UserProfile],
                     chat_context: str) -> str:
        """Build optimized prompt."""
        parts = ["השב בעברית ובאופן מהיר ומדויק."]

        if chat_context:
            # Limit to last 3 exchanges only for speed
            context_lines = chat_context.split('\n\n')
            recent_context = '\n\n'.join(context_lines[-6:])
            parts.append(f"הקשר אחרון: {recent_context}")

        parts.append(f"שאלה: {prompt}")
        return "\n\n".join(parts)