import streamlit as st
import os
from typing import Optional
from services import FirebaseService, AIService
from ui import PageManager, UIComponents
from models import UserProfile


class PoliticalChatbotApp:
    """Main application controller - handles routing and state management."""

    def __init__(self):
        self.data_service = FirebaseService()
        self.ai_service: Optional[AIService] = None
        self.page_manager: Optional[PageManager] = None
        self.ui = UIComponents()

    def run(self) -> None:
        """Main application entry point."""
        self._configure_page()
        self._initialize_session_state()
        self._initialize_services()
        self._route_to_page()

    def _configure_page(self) -> None:
        """Configure Streamlit page settings."""
        st.set_page_config(
            page_title="צ'אטבוט פוליטי",
            page_icon="🗳️",
            layout="wide"
        )
        self.ui.apply_rtl_styling()

    def _initialize_session_state(self) -> None:
        """Initialize session state variables."""
        # Initialize chat history
        if "messages" not in st.session_state:
            st.session_state.messages = []

        # Initialize app states
        if "app_mode" not in st.session_state:
            st.session_state.app_mode = "main_menu"
        if "questionnaire_completed" not in st.session_state:
            st.session_state.questionnaire_completed = False
        if "conversation_finished" not in st.session_state:
            st.session_state.conversation_finished = False
        if "admin_authenticated" not in st.session_state:
            st.session_state.admin_authenticated = False

    def _initialize_services(self) -> None:
        """Initialize AI service and page manager."""
        api_key = self._get_api_key()

        if api_key:
            self.ai_service = AIService(api_key)

        self.page_manager = PageManager(self.data_service, self.ai_service)

    def _get_api_key(self) -> Optional[str]:
        """Get API key from Streamlit secrets or environment variables."""
        try:
            # Try Streamlit secrets first
            api_key = st.secrets.get("GEMINI_API_KEY", "")
            if api_key:
                return api_key
        except Exception:
            pass

        # Fallback to environment variable
        api_key = os.getenv("GEMINI_API_KEY", "")
        return api_key if api_key else None

    def _route_to_page(self) -> None:
        """Route to appropriate page based on app state."""
        app_mode = st.session_state.get("app_mode", "main_menu")

        if app_mode == "main_menu":
            self.page_manager.render_main_menu()

        elif app_mode == "admin":
            if st.session_state.get("admin_authenticated", False):
                self.page_manager.render_admin_dashboard()
            else:
                # Redirect to main menu if not authenticated
                st.session_state.app_mode = "main_menu"
                st.rerun()

        elif app_mode == "user":
            self._handle_user_flow()

    def _handle_user_flow(self) -> None:
        """Handle the user flow (questionnaire -> chat -> final page)."""
        if st.session_state.get("conversation_finished", False):
            # Show final page
            self.page_manager.render_final_page()

        elif not self._is_questionnaire_completed():
            # Show questionnaire
            self.page_manager.render_questionnaire()

        else:
            # Show main chat interface
            if not self.ai_service:
                st.error("❌ מפתח API לא נמצא ברכיבי המערכת")
                st.markdown("אנא וודא שמפתח ה-API מוגדר נכון ברכיבי המערכת")

                # Navigation back to main menu
                if st.button("🔙 חזרה לתפריט הראשי", use_container_width=True):
                    st.session_state.app_mode = "main_menu"
                    st.rerun()
            else:
                self.page_manager.render_chat_interface()

    def _is_questionnaire_completed(self) -> bool:
        """Check if questionnaire is completed."""
        return st.session_state.get("questionnaire_completed", False)