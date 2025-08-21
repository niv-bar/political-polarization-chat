import streamlit as st
from typing import List, Any


class UIComponents:
    """Reusable UI components and styling."""

    @staticmethod
    def apply_rtl_styling() -> None:
        """Apply comprehensive Hebrew RTL styling."""
        rtl_css = """
        <style>
            /* Main content RTL */
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

            /* Text inputs */
            div[data-testid="stTextInput"] {direction: rtl;}
            div[data-testid="stTextInput"] label {
                direction: rtl !important;
                text-align: right !important;
            }
            div[data-testid="stTextInput"] input {
                direction: rtl !important;
                text-align: right !important;
            }
            div[data-testid="stTextInput"] input::placeholder {
                direction: rtl !important;
                text-align: right !important;
            }
            .stTextInput > label {direction: rtl; text-align: right;}
            .stTextInput input {direction: rtl; text-align: right !important;}

            /* Selectbox - Force RTL only on content, not structure */
            div[data-testid="stSelectbox"] {direction: rtl;}
            div[data-testid="stSelectbox"] label {
                direction: rtl !important;
                text-align: right !important;
            }
            /* Dropdown options */
            div[role="listbox"],
            div[role="option"],
            ul[role="listbox"],
            li[role="option"] {
                direction: rtl !important;
                text-align: right !important;
            }
            /* Selectbox content */
            .stSelectbox > div > div > div > div {
                direction: rtl !important;
                text-align: right !important;
            }

            /* Multiselect */
            div[data-testid="stMultiSelect"] {direction: rtl;}
            div[data-testid="stMultiSelect"] label {
                direction: rtl !important;
                text-align: right !important;
            }

            /* Slider - EXCLUDE from global RTL to preserve functionality */
            div[data-testid="stSlider"] {
                direction: ltr !important; /* Keep LTR for proper slider function */
            }
            div[data-testid="stSlider"] label {
                direction: rtl !important;
                text-align: right !important;
            }
            /* Slider track and thumb should stay LTR */
            .stSlider > div > div > div > div {
                direction: ltr !important;
            }
            /* Slider values */
            .stSlider .stMarkdown {
                direction: rtl !important;
                text-align: right !important;
            }

            /* Number input */
            div[data-testid="stNumberInput"] {direction: rtl;}
            div[data-testid="stNumberInput"] label {
                direction: rtl !important;
                text-align: right !important;
            }
            div[data-testid="stNumberInput"] input {
                direction: rtl !important;
                text-align: right !important;
            }

            /* Sidebar positioning to the right */
            .css-1d391kg {order: 2;}
            .main > div {order: 1;}
            section[data-testid="stSidebar"] {
                left: unset !important;
                right: 0 !important;
            }
            .css-1lcbmhc {
                left: unset !important;
                right: 0 !important;
            }
            .css-1d391kg {direction: rtl; text-align: right;}
            section[data-testid="stSidebar"] > div {direction: rtl; text-align: right;}
            section[data-testid="stSidebar"] .stButton > button {direction: rtl; text-align: right;}
            section[data-testid="stSidebar"] h1, 
            section[data-testid="stSidebar"] h2, 
            section[data-testid="stSidebar"] h3 {direction: rtl; text-align: right;}
            .main {margin-right: 21rem; margin-left: 1rem;}

            @media (max-width: 768px) {
                .main {margin-right: 1rem;}
            }
        </style>
        """
        st.markdown(rtl_css, unsafe_allow_html=True)

    @staticmethod
    def render_rtl_message(content: str) -> None:
        """Render message with RTL formatting."""
        st.markdown(
            f'<div style="direction: rtl; text-align: right;">{content}</div>',
            unsafe_allow_html=True
        )

    @staticmethod
    def render_header(title: str, subtitle: str = "", description: str = "") -> None:
        """Render page header with title and optional subtitle/description."""
        st.title(title)
        if subtitle:
            st.markdown(f"**{subtitle}**")
        if description:
            st.markdown(
                f'<div style="direction: rtl; text-align: right;">{description}</div>',
                unsafe_allow_html=True
            )
        st.markdown("---")

    @staticmethod
    def get_selectbox_index(options: List[str], value: str) -> int:
        """Get index of value in options list."""
        try:
            return options.index(value)
        except ValueError:
            return 0

    @staticmethod
    def render_footer() -> None:
        """Render application footer."""
        st.markdown("---")
        st.markdown(
            '<div style="direction: rtl; text-align: center; color: gray;">מחקר על קיטוב פוליטי | אוניברסיטה | 2025</div>',
            unsafe_allow_html=True
        )

    @staticmethod
    def show_loading(message: str = "טוען...") -> None:
        """Show loading spinner with message."""
        return st.spinner(message)

    @staticmethod
    def render_metrics(metrics: List[tuple]) -> None:
        """Render metrics in columns."""
        cols = st.columns(len(metrics))
        for i, (label, value) in enumerate(metrics):
            with cols[i]:
                st.metric(label, value)