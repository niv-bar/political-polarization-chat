import streamlit as st
from google import genai as google_genai
from google.genai import types
import warnings
from datetime import datetime
from typing import Optional, List, Dict, Any
from dataclasses import dataclass

# Suppress tqdm warnings for cleaner output
warnings.filterwarnings("ignore", category=UserWarning, module="tqdm")


@dataclass
class ChatMessage:
    """
    Data class representing a chat message.

    Attributes:
        role (str): The role of the message sender ('user' or 'assistant')
        content (str): The content of the message
        timestamp (str): When the message was created (for current session only)
    """
    role: str
    content: str
    timestamp: str = None

    def __post_init__(self):
        """Set timestamp if not provided."""
        if self.timestamp is None:
            self.timestamp = datetime.now().isoformat()


class UIManager:
    """
    Manages the user interface components and styling for the Streamlit app.

    This class handles page configuration, CSS styling for Hebrew RTL support,
    and UI component rendering.
    """

    @staticmethod
    def configure_page() -> None:
        """
        Configure the Streamlit page settings with Hebrew title and RTL layout.
        """
        st.set_page_config(
            page_title="צ'אטבוט פוליטי",  # Political Chatbot in Hebrew
            page_icon="🗳️",
            layout="wide"
        )

    @staticmethod
    def apply_rtl_styling() -> None:
        """
        Apply CSS styling for Hebrew RTL (Right-to-Left) text support.

        This method injects comprehensive CSS to ensure proper Hebrew text
        display and right-to-left layout throughout the application.
        """
        rtl_css = """
        <style>
            .main .block-container {direction: rtl;}
            .stChatMessage {direction: rtl; text-align: right;}
            .stChatMessage > div {direction: rtl; text-align: right;}
            .stMarkdown {direction: rtl; text-align: right;}
            .stMarkdown p {direction: rtl; text-align: right;}
            .css-1d391kg {direction: ltr;}
            .stChatInputContainer {direction: rtl;}
            .stChatInputContainer input {direction: rtl; text-align: right !important;}
            div[data-testid="stChatInput"] {direction: rtl;}
            div[data-testid="stChatInput"] input {direction: rtl; text-align: right !important;}
            div[data-testid="stChatInput"] input::placeholder {text-align: right; direction: rtl;}
            .stSelectbox > div > div {direction: rtl; text-align: right;}
            .stTextInput > div > div {direction: rtl; text-align: right;}
            .stButton > button {direction: rtl; text-align: right;}
            .stHeader {direction: rtl; text-align: right;}
            .stSubheader {direction: rtl; text-align: right;}
            .stTitle {direction: rtl; text-align: right;}
            .stWarning {direction: rtl; text-align: right;}
            .stInfo {direction: rtl; text-align: right;}
            .stSuccess {direction: rtl; text-align: right;}
            h1, h2, h3, h4, h5, h6 {direction: rtl; text-align: right;}
        </style>
        """
        st.markdown(rtl_css, unsafe_allow_html=True)

    @staticmethod
    def render_header() -> None:
        """
        Render the main header and divider for the application.
        """
        st.title("🗳️ צ'אטבוט פוליטי")  # Political Chatbot
        st.markdown("---")

    @staticmethod
    def render_rtl_message(content: str) -> None:
        """
        Render a message with proper RTL (Right-to-Left) formatting.

        Args:
            content (str): The message content to render
        """
        st.markdown(
            f'<div style="direction: rtl; text-align: right;">{content}</div>',
            unsafe_allow_html=True
        )


class SidebarManager:
    """
    Manages the sidebar components including settings and controls.

    This class handles API key input, chat history clearing, and other
    sidebar functionality.
    """

    def __init__(self):
        """Initialize the sidebar manager."""
        pass

    def render_sidebar(self) -> Optional[str]:
        """
        Render the sidebar with settings and controls.

        Returns:
            Optional[str]: The API key if provided, None otherwise
        """
        with st.sidebar:
            st.header("⚙️ הגדרות")  # Settings

            # API key input with session state persistence
            api_key = st.text_input(
                "🔑 מפתח API של Gemini:",  # Gemini API Key
                type="password",
                value=st.session_state.get("api_key", ""),
                help="הזן את מפתח ה-API שלך מ-Google AI Studio"  # Enter your API key from Google AI Studio
            )

            # Store API key in session state for persistence
            if api_key:
                st.session_state.api_key = api_key

            st.markdown("---")

            # Clear chat history button - session only
            if st.button("🗑️ נקה היסטוריית שיחה"):  # Clear chat history
                ChatHistoryManager.clear_history()
                st.rerun()

            return api_key

    def _clear_chat_history(self) -> None:
        """
        Clear the chat history from session state only.
        """
        st.session_state.messages = []


class GeminiClient:
    """
    Handles communication with Google's Gemini AI model.

    This class manages API configuration, request formatting, and response
    processing for the Gemini Flash model with web search capabilities.
    """

    def __init__(self, api_key: str):
        """
        Initialize the Gemini client with API key.

        Args:
            api_key (str): The Google AI Studio API key
        """
        self.api_key = api_key
        self._client = None
        self._config = None
        self._initialize_client()

    def _initialize_client(self) -> None:
        """
        Initialize the Gemini client and configuration.

        Sets up the client with web search tool and optimized parameters
        for political analysis.
        """
        try:
            self._client = google_genai.Client(api_key=self.api_key)

            # Configure web search tool for real-time information
            grounding_tool = types.Tool(google_search=types.GoogleSearch())

            # Optimized configuration for political chatbot
            self._config = types.GenerateContentConfig(
                tools=[grounding_tool],
                temperature=0.7,  # Balanced creativity for political analysis
                top_p=0.95,  # High diversity in token selection
                top_k=64,  # Moderate vocabulary restriction
                max_output_tokens=8192,  # Extended responses for detailed analysis
            )
        except Exception as e:
            st.error(f"❌ Failed to initialize Gemini client: {str(e)}")
            self._client = None

    def generate_response(self, prompt: str) -> str:
        """
        Generate a response from Gemini with web search capabilities.

        Args:
            prompt (str): The user's input prompt

        Returns:
            str: The generated response or error message
        """
        if not self._client or not self._config:
            return "❌ שגיאה: הלקוח לא מוכן"  # Error: Client not ready

        try:
            response = self._client.models.generate_content(
                model="gemini-2.5-flash",
                contents=prompt,
                config=self._config,
            )
            return response.text
        except Exception as e:
            return f"❌ שגיאה ב-Gemini: {str(e)}"  # Error in Gemini


class ChatHistoryManager:
    """
    Manages chat message history and session state for current session only.

    This class handles storing, retrieving, and managing chat messages
    in Streamlit's session state. Messages persist only during the current
    browser session and are cleared when the session ends or manually cleared.
    """

    @staticmethod
    def initialize_chat_history() -> None:
        """
        Initialize chat history in session state if not already present.
        Only creates empty history for new sessions.
        """
        if "messages" not in st.session_state:
            st.session_state.messages = []

    @staticmethod
    def add_message(role: str, content: str) -> None:
        """
        Add a new message to the current session's chat history.

        Args:
            role (str): The role of the message sender ('user' or 'assistant')
            content (str): The content of the message
        """
        message = ChatMessage(role=role, content=content)
        message_dict = {
            "role": message.role,
            "content": message.content,
            "timestamp": message.timestamp
        }

        # Add to current session state only
        st.session_state.messages.append(message_dict)

    @staticmethod
    def get_messages() -> List[Dict[str, str]]:
        """
        Retrieve all messages from current session's chat history.

        Returns:
            List[Dict[str, str]]: List of message dictionaries from current session
        """
        return st.session_state.get("messages", [])

    @staticmethod
    def clear_history() -> None:
        """
        Clear the current session's chat history.
        """
        st.session_state.messages = []

    @staticmethod
    def render_chat_history() -> None:
        """
        Render all chat messages from current session in the chat interface.
        """
        for message in ChatHistoryManager.get_messages():
            with st.chat_message(message["role"]):
                UIManager.render_rtl_message(message["content"])

    @staticmethod
    def get_chat_context() -> str:
        """
        Get the full chat context as a formatted string for AI context.

        Returns:
            str: Formatted chat history for providing context to AI
        """
        messages = ChatHistoryManager.get_messages()
        if not messages:
            return ""

        context_parts = []
        for msg in messages:
            role_label = "משתמש" if msg["role"] == "user" else "עוזר"  # User or Assistant
            context_parts.append(f"{role_label}: {msg['content']}")

        return "\n\n".join(context_parts)


class PoliticalChatbot:
    """
    Main political chatbot application class.

    This class orchestrates the entire chatbot application, managing UI,
    chat history, and AI interactions for political discussions.
    """

    def __init__(self):
        """
        Initialize the political chatbot application.
        """
        self.ui_manager = UIManager()
        self.sidebar_manager = SidebarManager()
        self.chat_history = ChatHistoryManager()
        self._gemini_client: Optional[GeminiClient] = None

    def setup_ui(self) -> None:
        """
        Set up the user interface components and styling.
        """
        self.ui_manager.configure_page()
        self.ui_manager.apply_rtl_styling()
        self.ui_manager.render_header()

    def initialize_session_state(self) -> None:
        """
        Initialize all necessary session state variables.
        """
        self.chat_history.initialize_chat_history()

    def handle_sidebar(self) -> Optional[str]:
        """
        Handle sidebar rendering and return API key if available.

        Returns:
            Optional[str]: The API key if provided, None otherwise
        """
        return self.sidebar_manager.render_sidebar()

    def _initialize_gemini_client(self, api_key: str) -> None:
        """
        Initialize or update the Gemini client with the provided API key.

        Args:
            api_key (str): The Google AI Studio API key
        """
        if not self._gemini_client or self._gemini_client.api_key != api_key:
            self._gemini_client = GeminiClient(api_key)

    def handle_user_input(self, api_key: str) -> None:
        """
        Handle user input and generate AI responses.

        Args:
            api_key (str): The Google AI Studio API key
        """
        # Initialize Gemini client with current API key
        self._initialize_gemini_client(api_key)

        # Render existing chat history
        self.chat_history.render_chat_history()

        # Handle new user input with context awareness
        if prompt := st.chat_input("כתוב כאן..."):  # Write here...
            # Add user message to current session history
            self.chat_history.add_message("user", prompt)

            # Display user message
            with st.chat_message("user"):
                self.ui_manager.render_rtl_message(prompt)

            # Generate and display assistant response with full context
            with st.chat_message("assistant"):
                with st.spinner("🔍 מחפש מידע עדכני..."):  # Searching for current information...
                    # Get chat context for better responses
                    chat_context = self.chat_history.get_chat_context()

                    # Enhanced prompt with context if available
                    enhanced_prompt = prompt
                    if chat_context:
                        enhanced_prompt = f"הקשר השיחה הקודם:\n{chat_context}\n\nשאלה נוכחית: {prompt}"

                    response_text = self._gemini_client.generate_response(enhanced_prompt)
                    self.ui_manager.render_rtl_message(response_text)

                    # Add assistant response to current session history
                    self.chat_history.add_message("assistant", response_text)

    def display_api_key_warning(self) -> None:
        """
        Display warning and information when API key is not provided.
        """
        st.warning("⚠️ אנא הזן מפתח API של Google Gemini בצד שמאל.")  # Please enter Google Gemini API key on the left
        st.info(
            "💡 קבל מפתח API חינמי מ-[Google AI Studio](https://makersuite.google.com/app/apikey)")  # Get free API key from Google AI Studio

    def run(self) -> None:
        """
        Main application entry point that orchestrates the entire chatbot.

        This method sets up the UI, handles user interactions, and manages
        the chat flow from start to finish.
        """
        # Setup UI and initialize session state
        self.setup_ui()
        self.initialize_session_state()

        # Handle sidebar and get API key
        api_key = self.handle_sidebar()

        # Main application logic
        if not api_key:
            self.display_api_key_warning()
        else:
            self.handle_user_input(api_key)


def main() -> None:
    """
    Application entry point.

    Creates and runs the political chatbot application.
    """
    chatbot = PoliticalChatbot()
    chatbot.run()


# Run the application
if __name__ == "__main__":
    main()