import streamlit as st
from google import genai as google_genai
from google.genai import types
import warnings
import os
from datetime import datetime
from typing import Optional, List, Dict
from dataclasses import dataclass

warnings.filterwarnings("ignore", category=UserWarning, module="tqdm")


@dataclass
class ChatMessage:
    """Data class for chat messages with automatic timestamp."""
    role: str
    content: str
    timestamp: str = None

    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = datetime.now().isoformat()


class UIManager:
    """Manages UI components and Hebrew RTL styling."""

    @staticmethod
    def configure_page() -> None:
        st.set_page_config(
            page_title="צ'אטבוט פוליטי",
            page_icon="🗳️",
            layout="wide"
        )

    @staticmethod
    def apply_rtl_styling() -> None:
        """Apply comprehensive Hebrew RTL styling."""
        rtl_css = """
        <style>
            .main .block-container {direction: rtl;}
            .stChatMessage {direction: rtl; text-align: right;}
            .stChatMessage > div {direction: rtl; text-align: right;}
            .stMarkdown {direction: rtl; text-align: right;}
            .stMarkdown p {direction: rtl; text-align: right;}
            .stChatInputContainer {direction: rtl;}
            .stChatInputContainer input {direction: rtl; text-align: right !important;}
            div[data-testid="stChatInput"] {direction: rtl;}
            div[data-testid="stChatInput"] input {direction: rtl; text-align: right !important;}
            div[data-testid="stChatInput"] input::placeholder {text-align: right; direction: rtl;}
            .stButton > button {direction: rtl; text-align: right;}
            .stWarning, .stInfo, .stSuccess, .stError {direction: rtl; text-align: right;}
            h1, h2, h3, h4, h5, h6 {direction: rtl; text-align: right;}
        </style>
        """
        st.markdown(rtl_css, unsafe_allow_html=True)

    @staticmethod
    def render_header() -> None:
        st.title("🗳️ צ'אטבוט פוליטי")
        st.markdown("---")

    @staticmethod
    def render_rtl_message(content: str) -> None:
        st.markdown(
            f'<div style="direction: rtl; text-align: right;">{content}</div>',
            unsafe_allow_html=True
        )


class SidebarManager:
    """Manages sidebar controls."""

    def render_sidebar(self) -> None:
        with st.sidebar:
            st.header("⚙️ הגדרות")

            if st.button("🗑️ נקה היסטוריית שיחה"):
                ChatHistoryManager.clear_history()
                st.rerun()


class GeminiClient:
    """Handles Gemini AI communication with web search."""

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

    def generate_response(self, prompt: str) -> str:
        """Generate response with web search."""
        if not self._client or not self._config:
            return "❌ שגיאה: הלקוח לא מוכן"

        try:
            enhanced_prompt = f"""
IMPORTANT: Use web search to get current, real-time information before answering.
אנא חפש באינטרנט מידע עדכני לפני המענה. השתמש בחיפוש ברשת לקבלת מידע נוכחי ומדויק.

שאלת המשתמש: {prompt}

חפש ברשת מידע עדכני הקשור לשאלה זו לפני שאתה עונה.
"""
            response = self._client.models.generate_content(
                model="gemini-2.5-flash",
                contents=enhanced_prompt,
                config=self._config,
            )
            return response.text
        except Exception as e:
            return f"❌ שגיאה ב-Gemini: {str(e)}"


class ChatHistoryManager:
    """Manages chat history in session state."""

    @staticmethod
    def initialize_chat_history() -> None:
        if "messages" not in st.session_state:
            st.session_state.messages = []

    @staticmethod
    def add_message(role: str, content: str) -> None:
        message = ChatMessage(role=role, content=content)
        message_dict = {
            "role": message.role,
            "content": message.content,
            "timestamp": message.timestamp
        }
        st.session_state.messages.append(message_dict)

    @staticmethod
    def get_messages() -> List[Dict[str, str]]:
        return st.session_state.get("messages", [])

    @staticmethod
    def clear_history() -> None:
        st.session_state.messages = []

    @staticmethod
    def render_chat_history() -> None:
        for message in ChatHistoryManager.get_messages():
            with st.chat_message(message["role"]):
                UIManager.render_rtl_message(message["content"])

    @staticmethod
    def get_chat_context() -> str:
        """Get formatted chat context for AI."""
        messages = ChatHistoryManager.get_messages()
        if not messages:
            return ""

        context_parts = []
        for msg in messages:
            role_label = "משתמש" if msg["role"] == "user" else "עוזר"
            context_parts.append(f"{role_label}: {msg['content']}")

        return "\n\n".join(context_parts)


class PoliticalChatbot:
    """Main political chatbot application."""

    def __init__(self):
        self.ui_manager = UIManager()
        self.sidebar_manager = SidebarManager()
        self.chat_history = ChatHistoryManager()
        self._gemini_client: Optional[GeminiClient] = None

    def setup_ui(self) -> None:
        self.ui_manager.configure_page()
        self.ui_manager.apply_rtl_styling()
        self.ui_manager.render_header()

    def initialize_session_state(self) -> None:
        self.chat_history.initialize_chat_history()

    def _get_api_key(self) -> Optional[str]:
        """Get API key from Streamlit secrets or environment variables."""
        try:
            api_key = st.secrets.get("GEMINI_API_KEY", "")
            if api_key:
                return api_key
        except Exception:
            pass

        api_key = os.getenv("GEMINI_API_KEY", "")
        return api_key if api_key else None

    def handle_sidebar(self) -> None:
        self.sidebar_manager.render_sidebar()

    def _initialize_gemini_client(self, api_key: str) -> None:
        if not self._gemini_client or self._gemini_client.api_key != api_key:
            self._gemini_client = GeminiClient(api_key)

    def handle_user_input(self, api_key: str) -> None:
        """Handle user input and generate AI responses."""
        self._initialize_gemini_client(api_key)
        self.chat_history.render_chat_history()

        if prompt := st.chat_input("כתוב כאן..."):
            # Add and display user message
            self.chat_history.add_message("user", prompt)
            with st.chat_message("user"):
                self.ui_manager.render_rtl_message(prompt)

            # Generate and display AI response
            with st.chat_message("assistant"):
                with st.spinner("🔍 מחפש מידע עדכני..."):
                    chat_context = self.chat_history.get_chat_context()

                    if chat_context:
                        enhanced_prompt = f"""
אנא ענה בדיוק ובהתבסס על מידע עדכני ומדויק מחיפוש באינטרנט.
אם אתה צריך מידע על תאריכים או אירועים עדכניים, חפש את המידע הנוכחי.

הקשר השיחה הקודם:
{chat_context}

שאלה נוכחית: {prompt}
"""
                    else:
                        enhanced_prompt = prompt

                    response_text = self._gemini_client.generate_response(enhanced_prompt)
                    self.ui_manager.render_rtl_message(response_text)
                    self.chat_history.add_message("assistant", response_text)

    def display_api_key_warning(self) -> None:
        st.error("❌ מפתח API לא נמצא ברכיבי המערכת")

    def run(self) -> None:
        """Main application entry point."""
        self.setup_ui()
        self.initialize_session_state()

        self.handle_sidebar()
        api_key = self._get_api_key()

        if not api_key:
            self.display_api_key_warning()
        else:
            self.handle_user_input(api_key)


def main() -> None:
    """Application entry point."""
    chatbot = PoliticalChatbot()
    chatbot.run()


if __name__ == "__main__":
    main()