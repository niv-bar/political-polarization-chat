import streamlit as st
from google import genai as google_genai
from google.genai import types
import warnings
import os
import json
import uuid
from datetime import datetime
from typing import Optional, List, Dict, Any
from dataclasses import dataclass, asdict

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


@dataclass
class UserProfile:
    """Data class for user demographic and political profile."""
    # Session Info
    session_id: str = ""
    created_at: str = ""

    # Demographic Data
    gender: str = ""
    age: int = 0
    marital_status: str = ""
    region: str = ""
    religiosity: int = 0

    # Political Data
    political_stance: int = 0
    protest_participation: str = ""
    influence_sources: List[str] = None

    # Polarization Measurements
    feeling_thermometer: Dict[str, int] = None
    social_distance: Dict[str, int] = None

    def __post_init__(self):
        if self.session_id == "":
            self.session_id = str(uuid.uuid4())
        if self.created_at == "":
            self.created_at = datetime.now().isoformat()
        if self.influence_sources is None:
            self.influence_sources = []
        if self.feeling_thermometer is None:
            self.feeling_thermometer = {}
        if self.social_distance is None:
            self.social_distance = {}


class QuestionnaireManager:
    """Manages the user questionnaire for demographic and political profiling."""

    def __init__(self):
        self.ui_manager = UIManager()

    def render_questionnaire(self) -> bool:
        """Render the questionnaire and return True if completed."""
        self.ui_manager.render_header_questionnaire()

        with st.form("user_questionnaire"):
            st.markdown("### 📊 מידע דמוגרפי")

            # Demographic Questions
            gender = st.selectbox(
                "מגדר:",
                options=["", "זכר", "נקבה", "אחר", "מעדיף/ה לא לענות"],
                help="בחר/י את המגדר שלך"
            )

            age = st.number_input(
                "גיל:",
                min_value=18, max_value=120, value=25,
                help="הזן/י את גילך"
            )

            marital_status = st.selectbox(
                "מצב משפחתי:",
                options=["", "רווק/ה", "נשוי/אה", "גרוש/ה", "אלמן/ה", "בזוגיות"],
                help="בחר/י את מצבך המשפחתי"
            )

            region = st.selectbox(
                "אזור מגורים:",
                options=["", "צפון", "חיפה והצפון", "מרכז", "ירושלים", "דרום", "יהודה ושומרון"],
                help="בחר/י את אזור המגורים שלך"
            )

            religiosity = st.slider(
                "רמת דתיות (1=חילוני לגמרי, 10=דתי מאוד):",
                min_value=1, max_value=10, value=5,
                help="דרג/י את רמת הדתיות שלך"
            )

            st.markdown("### 🗳️ מידע פוליטי")

            political_stance = st.slider(
                "עמדה פוליטית (1=שמאל קיצוני, 10=ימין קיצוני):",
                min_value=1, max_value=10, value=5,
                help="איפה אתה ממקם את עצמך בספקטרום הפוליטי?"
            )

            protest_participation = st.selectbox(
                "השתתפות בהפגנות בשנה האחרונה:",
                options=["", "לא השתתפתי", "השתתפתי מדי פעם", "השתתפתי רבות", "השתתפתי באופן קבוע"],
                help="באיזו מידה השתתפת בהפגנות?"
            )

            influence_sources = st.multiselect(
                "מקורות השפעה על דעותיך הפוליטיות:",
                options=["משפחה", "חברים", "מדיה מסורתית", "רשתות חברתיות", "פוליטיקאים", "אקדמיה",
                         "דת/מנהיגים רוחניים", "ניסיון אישי"],
                help="בחר/י את המקורות המשפיעים על דעותיך"
            )

            st.markdown("### 🌡️ מדדי קיטוב - מדי חום רגשי")
            st.caption("דרג/י את הרגש שלך כלפי מפלגות שונות (0=קר מאוד/שנאה חזקה, 100=חם מאוד/אהדה חזקה)")

            parties = ["ליכוד", "יש עתיד", "הציונות הדתית", "יהדות התורה", "העבודה", "מרץ", "ש״ס", "ישראל ביתנו"]
            feeling_thermometer = {}

            col1, col2 = st.columns(2)
            for i, party in enumerate(parties):
                with col1 if i % 2 == 0 else col2:
                    feeling_thermometer[party] = st.slider(
                        f"{party}:",
                        min_value=0, max_value=100, value=50,
                        help=f"איך אתה מרגיש כלפי {party}?"
                    )

            st.markdown("### 🤝 מדד מרחק חברתי")
            st.caption("עד כמה היית מרגיש בנוח במצבים הבאים עם אנשים בעלי דעות פוליטיות שונות ממך?")
            st.caption("(1=מאוד לא נוח, 6=מאוד נוח)")

            social_situations = [
                "לחיות באותה השכונה",
                "לעבוד באותו מקום עבודה",
                "להיות חברים קרובים",
                "שבן/בת המשפחה שלי יתחתן עם מישהו מהקבוצה הזו"
            ]

            social_distance = {}
            for situation in social_situations:
                social_distance[situation] = st.slider(
                    f"{situation}:",
                    min_value=1, max_value=6, value=3,
                    help=f"עד כמה נוח לך ש{situation}?"
                )

            st.markdown("---")

            # Option to skip validation
            skip_validation = st.checkbox(
                "דלג על שדות חובה ומעבר ישירות לצ'אט",
                help="סמן/י כדי לדלג על מילוי שדות חובה ולעבור ישירות לצ'אט"
            )

            submitted = st.form_submit_button("המשך לצ'אט 💬", use_container_width=True)

            if submitted:
                # Validate required fields only if not skipping
                if not skip_validation and not all([gender, marital_status, region, protest_participation]):
                    st.error("אנא מלא/י את כל השדות הנדרשים או סמן/י 'דלג על שדות חובה'")
                    return False

                # Create user profile with session ID
                user_profile = UserProfile(
                    gender=gender,
                    age=age if age > 18 else 18,  # Ensure minimum age
                    marital_status=marital_status,
                    region=region,
                    religiosity=religiosity,
                    political_stance=political_stance,
                    protest_participation=protest_participation,
                    influence_sources=influence_sources,
                    feeling_thermometer=feeling_thermometer,
                    social_distance=social_distance
                )

                # Save to session state only (no automatic file saving)
                self._save_user_profile(user_profile)

                st.success(f"פרופיל נשמר בהצלחה! (מזהה: {user_profile.session_id[:8]}) מועבר לצ'אט...")
                st.rerun()

        return False

    def _save_user_profile(self, profile: UserProfile) -> None:
        """Save user profile to session state only."""
        st.session_state.user_profile = profile
        st.session_state.questionnaire_completed = True

    def is_questionnaire_completed(self) -> bool:
        """Check if questionnaire is completed."""
        return st.session_state.get("questionnaire_completed", False)


class FinalPageManager:
    """Manages the final page after conversation completion."""

    def __init__(self):
        self.ui_manager = UIManager()

    def render_final_page(self) -> None:
        """Render the final page with option to save data."""
        self.ui_manager.render_header_final()

        # Show conversation summary
        messages = ChatHistoryManager.get_messages()
        message_count = len(messages)
        user_messages = len([m for m in messages if m["role"] == "user"])

        st.markdown("### 📊 סיכום השיחה")
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("סך הודעות", message_count)
        with col2:
            st.metric("הודעות משתמש", user_messages)
        with col3:
            st.metric("הודעות בוט", message_count - user_messages)

        st.markdown("---")

        # Data saving options
        st.markdown("### 💾 שמירת נתונים למחקר")
        st.markdown(
            '<div style="direction: rtl; text-align: right;">האם תרצה לשמור את נתוני השיחה למחקר על קיטוב פוליטי? הנתונים נשמרים באופן אנונימי.</div>',
            unsafe_allow_html=True
        )

        col1, col2, col3 = st.columns([1, 1, 1])

        with col2:
            if st.button("💾 שמור נתונים למחקר", use_container_width=True, type="primary"):
                self._save_conversation_data()
                st.success("✅ הנתונים נשמרו בהצלחה! תודה על ההשתתפות במחקר.")
                st.balloons()

        st.markdown("---")

        # Navigation options
        st.markdown("### 🔄 אפשרויות נוספות")
        col1, col2 = st.columns(2)

        with col1:
            if st.button("🔙 חזרה לשאלון", use_container_width=True):
                self._reset_to_questionnaire()

        with col2:
            if st.button("🏠 התחל מחדש", use_container_width=True):
                self._reset_application()

    def _save_conversation_data(self) -> None:
        """Save conversation data with user profile to JSON."""
        try:
            # Get user profile and messages
            profile = st.session_state.get("user_profile")
            messages = ChatHistoryManager.get_messages()

            if not profile:
                st.error("שגיאה: לא נמצא פרופיל משתמש")
                return

            # Debug info
            st.info(f"נמצאו {len(messages)} הודעות לשמירה")

            # Create complete session data
            session_data = {
                "session_id": profile.session_id,
                "created_at": profile.created_at,
                "finished_at": datetime.now().isoformat(),
                "user_profile": asdict(profile),
                "conversation": messages,
                "conversation_stats": {
                    "total_messages": len(messages),
                    "user_messages": len([m for m in messages if m["role"] == "user"]),
                    "bot_messages": len([m for m in messages if m["role"] == "assistant"]),
                    "duration_minutes": self._calculate_duration(messages)
                }
            }

            # Debug: show what we're saving
            if len(messages) == 0:
                st.warning("אין הודעות לשמירה - השיחה ריקה")
                return

            # Ensure data directory exists
            os.makedirs("conversation_data", exist_ok=True)

            # Save complete session data
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"conversation_data/complete_session_{profile.session_id[:8]}_{timestamp}.json"

            with open(filename, 'w', encoding='utf-8') as f:
                json.dump(session_data, f, ensure_ascii=False, indent=2)

            # Also append to master conversation file
            master_file = "conversation_data/all_conversations.jsonl"
            with open(master_file, 'a', encoding='utf-8') as f:
                json.dump(session_data, f, ensure_ascii=False)
                f.write('\n')

            st.info(f"נתונים נשמרו בקובץ: {filename}")

        except Exception as e:
            st.error(f"שגיאה בשמירת השיחה: {str(e)}")
            st.exception(e)  # Show full error details

    def _calculate_duration(self, messages: List[Dict]) -> float:
        """Calculate conversation duration in minutes."""
        if not messages or len(messages) < 2:
            return 0.0

        try:
            start_time = datetime.fromisoformat(messages[0]["timestamp"])
            end_time = datetime.fromisoformat(messages[-1]["timestamp"])
            duration = (end_time - start_time).total_seconds() / 60
            return round(duration, 2)
        except:
            return 0.0

    def _reset_to_questionnaire(self) -> None:
        """Reset to questionnaire page."""
        st.session_state.questionnaire_completed = False
        st.session_state.conversation_finished = False
        if "user_profile" in st.session_state:
            del st.session_state.user_profile
        ChatHistoryManager.clear_history()
        st.rerun()

    def _reset_application(self) -> None:
        """Reset entire application."""
        # Clear all session state
        for key in list(st.session_state.keys()):
            del st.session_state[key]
        st.rerun()


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
            .stSelectbox > label {direction: rtl; text-align: right;}
            .stSlider > label {direction: rtl; text-align: right;}
            .stMultiSelect > label {direction: rtl; text-align: right;}
            .stNumberInput > label {direction: rtl; text-align: right;}
            .stMetric {direction: rtl; text-align: right;}
            h1, h2, h3, h4, h5, h6 {direction: rtl; text-align: right;}
        </style>
        """
        st.markdown(rtl_css, unsafe_allow_html=True)

    @staticmethod
    def render_header() -> None:
        st.title("🗳️ צ'אטבוט פוליטי")
        st.markdown("---")

    @staticmethod
    def render_header_questionnaire() -> None:
        st.title("📋 שאלון מאפיינים אישיים ופוליטיים")
        st.markdown("**אנא מלא/י את השאלון הבא לפני תחילת השיחה עם הבוט**")
        st.markdown(
            '<div style="direction: rtl; text-align: right;">המידע נשמר באופן אנונימי ומשמש למחקר על קיטוב פוליטי</div>',
            unsafe_allow_html=True
        )
        st.markdown("---")

    @staticmethod
    def render_header_final() -> None:
        st.title("🎯 סיום השיחה")
        st.markdown("**תודה על השתתפותך בשיחה עם הבוט הפוליטי!**")
        st.markdown(
            '<div style="direction: rtl; text-align: right;">להלן סיכום השיחה ואפשרות לשמור את הנתונים למחקר</div>',
            unsafe_allow_html=True
        )
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

            # Back to questionnaire button
            if st.button("🔙 חזרה לשאלון"):
                st.session_state.questionnaire_completed = False
                if "user_profile" in st.session_state:
                    del st.session_state.user_profile
                st.rerun()

            st.markdown("---")

            # Finish conversation button
            if st.button("✅ סיים שיחה"):
                st.session_state.conversation_finished = True
                st.rerun()

            st.markdown("---")

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
        self.questionnaire_manager = QuestionnaireManager()
        self.final_page_manager = FinalPageManager()
        self.sidebar_manager = SidebarManager()
        self.chat_history = ChatHistoryManager()
        self._gemini_client: Optional[GeminiClient] = None

    def setup_ui(self) -> None:
        self.ui_manager.configure_page()
        self.ui_manager.apply_rtl_styling()

    def initialize_session_state(self) -> None:
        self.chat_history.initialize_chat_history()
        # Initialize questionnaire state
        if "questionnaire_completed" not in st.session_state:
            st.session_state.questionnaire_completed = False
        if "conversation_finished" not in st.session_state:
            st.session_state.conversation_finished = False

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

                    # Get user profile context
                    user_context = self._get_user_context()

                    if chat_context:
                        enhanced_prompt = f"""
אנא ענה בדיוק ובהתבסס על מידע עדכני ומדויק מחיפוש באינטרנט.
אם אתה צריך מידע על תאריכים או אירועים עדכניים, חפש את המידע הנוכחי.

{user_context}

הקשר השיחה הקודם:
{chat_context}

שאלה נוכחית: {prompt}
"""
                    else:
                        enhanced_prompt = f"""
{user_context}

{prompt}
"""

                    response_text = self._gemini_client.generate_response(enhanced_prompt)
                    self.ui_manager.render_rtl_message(response_text)
                    self.chat_history.add_message("assistant", response_text)

    def _get_user_context(self) -> str:
        """Generate user context from questionnaire data."""
        if "user_profile" not in st.session_state:
            return ""

        profile = st.session_state.user_profile
        context = f"""
מידע על המשתמש (להתאמת התגובות):
- גיל: {profile.age}
- אזור: {profile.region}  
- עמדה פוליטית: {profile.political_stance}/10 (1=שמאל, 10=ימין)
- רמת דתיות: {profile.religiosity}/10
- השתתפות בהפגנות: {profile.protest_participation}

התאם את התשובות לפרופיל המשתמש תוך שמירה על אובייקטיביות ואיזון.
"""
        return context

    def display_api_key_warning(self) -> None:
        st.error("❌ מפתח API לא נמצא ברכיבי המערכת")

    def run(self) -> None:
        """Main application entry point."""
        self.setup_ui()
        self.initialize_session_state()

        # Check conversation flow state
        if st.session_state.get("conversation_finished", False):
            # Show final page
            self.final_page_manager.render_final_page()
        elif not self.questionnaire_manager.is_questionnaire_completed():
            # Show questionnaire
            self.questionnaire_manager.render_questionnaire()
        else:
            # Show main chatbot
            self.ui_manager.render_header()
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