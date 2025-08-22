import streamlit as st
from google import genai as google_genai
from google.genai import types
from typing import Optional, Generator
from models import UserProfile

class AIService:
    """Handles AI interactions with streaming responses."""

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
        """Generate optimized streaming response."""
        if not self._client:
            yield "❌ שגיאה: הלקוח לא מוכן"
            return

        try:
            enhanced_prompt = self._build_prompt(prompt, user_profile, chat_context)

            # Optimized configuration
            config = types.GenerateContentConfig(
                tools=[types.Tool(google_search=types.GoogleSearch())],
                temperature=0.7,
                top_p=0.85,
                top_k=30,
                max_output_tokens=2500,
                candidate_count=1,
            )

            # Start streaming
            response_stream = self._client.models.generate_content_stream(
                model="gemini-2.5-flash",
                contents=enhanced_prompt,
                config=config,
            )

            # Yield chunks
            for chunk in response_stream:
                if hasattr(chunk, 'text') and chunk.text:
                    yield chunk.text

        except Exception as e:
            yield f"❌ שגיאה ב-Gemini: {str(e)}"

    def _build_prompt(self, prompt: str, user_profile: Optional[UserProfile],
                     chat_context: str) -> str:
        """Build optimized prompt."""
        parts = ["השב בעברית. חפש מידע עדכני אם נדרש."]

        if user_profile:
            parts.append(f"משתמש: גיל {user_profile.age}, אזור {user_profile.region}, עמדה פוליטית {user_profile.political_stance}/10")

        if chat_context:
            # Limit to last 4 exchanges only
            context_lines = chat_context.split('\n\n')
            recent_context = '\n\n'.join(context_lines[-8:])
            parts.append(f"הקשר: {recent_context}")

        parts.append(f"שאלה: {prompt}")
        return "\n\n".join(parts)