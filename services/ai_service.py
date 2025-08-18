import streamlit as st
from google import genai as google_genai
from google.genai import types
from typing import Optional
from models import UserProfile


class AIService:
    """Handles AI interactions with context management."""

    def __init__(self, api_key: str):
        self.api_key = api_key
        self._client = None
        self._config = None
        self._initialize_client()

    def _initialize_client(self) -> None:
        """Initialize Gemini client with web search tool."""
        try:
            self._client = google_genai.Client(api_key=self.api_key)
            grounding_tool = types.Tool(google_search=types.GoogleSearch())

            self._config = types.GenerateContentConfig(
                tools=[grounding_tool],
                temperature=0.7,
                top_p=0.95,
                top_k=64,
                max_output_tokens=8192,
            )
        except Exception as e:
            st.error(f"❌ Failed to initialize Gemini client: {str(e)}")
            self._client = None

    def generate_response(self, prompt: str, user_profile: Optional[UserProfile] = None,
                          chat_context: str = "") -> str:
        """Generate response with web search and context."""
        if not self._client or not self._config:
            return "❌ שגיאה: הלקוח לא מוכן"

        try:
            enhanced_prompt = self._build_enhanced_prompt(prompt, user_profile, chat_context)

            response = self._client.models.generate_content(
                model="gemini-2.5-flash",
                contents=enhanced_prompt,
                config=self._config,
            )
            return response.text

        except Exception as e:
            return f"❌ שגיאה ב-Gemini: {str(e)}"

    def _build_enhanced_prompt(self, prompt: str, user_profile: Optional[UserProfile],
                               chat_context: str) -> str:
        """Build enhanced prompt with context."""
        parts = [
            "IMPORTANT: Use web search to get current, real-time information before answering.",
            "אנא חפש באינטרנט מידע עדכני לפני המענה. השתמש בחיפוש ברשת לקבלת מידע נוכחי ומדויק."
        ]

        if user_profile:
            user_context = self._build_user_context(user_profile)
            parts.append(user_context)

        if chat_context:
            parts.append(f"הקשר השיחה הקודם:\n{chat_context}")

        parts.append(f"שאלת המשתמש: {prompt}")
        parts.append("חפש ברשת מידע עדכני הקשור לשאלה זו לפני שאתה עונה.")

        return "\n\n".join(parts)

    def _build_user_context(self, profile: UserProfile) -> str:
        """Generate user context from profile data."""
        return f"""
מידע על המשתמש (להתאמת התגובות):
- גיל: {profile.age}
- אזור: {profile.region}  
- עמדה פוליטית: {profile.political_stance}/10 (1=שמאל, 10=ימין)
- רמת דתיות: {profile.religiosity}/10
- השתתפות בהפגנות: {profile.protest_participation}

התאם את התשובות לפרופיל המשתמש תוך שמירה על אובייקטיביות ואיזון.
"""