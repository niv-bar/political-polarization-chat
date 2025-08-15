"""
Political Polarization Reduction Chat Application
MLDS Final Project - Conversational Agents for Reducing Political Polarization
"""

import streamlit as st
from google import genai as google_genai
from google.genai import types
import os
import warnings
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Suppress warnings
warnings.filterwarnings("ignore", category=UserWarning, module="tqdm")

# Page configuration
st.set_page_config(
    page_title="מערכת הפחתת קיטוב פוליטי - MLDS",
    page_icon="🤖",
    layout="wide"
)

# Hebrew RTL support CSS
st.markdown("""
<style>
    .main .block-container {
        direction: rtl;
        text-align: right;
    }

    .stChatMessage {
        direction: rtl;
        text-align: right;
    }

    .stChatMessage > div {
        direction: rtl;
        text-align: right;
    }

    .stMarkdown {
        direction: rtl;
        text-align: right;
    }

    .stMarkdown p {
        direction: rtl;
        text-align: right;
    }

    .stChatInputContainer {
        direction: rtl;
    }

    .stChatInputContainer input {
        direction: rtl;
        text-align: right !important;
    }

    div[data-testid="stChatInput"] {
        direction: rtl;
    }

    div[data-testid="stChatInput"] input {
        direction: rtl;
        text-align: right !important;
    }

    div[data-testid="stChatInput"] input::placeholder {
        text-align: right;
        direction: rtl;
    }

    .main h1, .main h2, .main h3 {
        direction: rtl;
        text-align: right;
    }

    .css-1d391kg {
        direction: ltr;
    }
</style>
""", unsafe_allow_html=True)

# Get API key from environment or Streamlit secrets
def get_api_key():
    """Get Gemini API key from environment variables or Streamlit secrets"""
    try:
        # Try Streamlit secrets first (for deployment)
        return st.secrets["GEMINI_API_KEY"]
    except (KeyError, FileNotFoundError):
        # Fallback to environment variable
        api_key = os.getenv("GEMINI_API_KEY")
        if api_key:
            return api_key
        return None

def get_gemini_response(prompt, api_key, model_name="gemini-2.5-flash", temp=0.7):
    """Generate response using Gemini with web search"""
    try:
        client = google_genai.Client(api_key=api_key)

        # Configure grounding tool for web search
        grounding_tool = types.Tool(google_search=types.GoogleSearch())
        
        # Set up generation configuration
        generation_config = types.GenerateContentConfig(
            tools=[grounding_tool],
            temperature=temp,
            top_p=0.95,
            top_k=64,
            max_output_tokens=8192,
        )
        
        # Generate content with web search
        response = client.models.generate_content(
            model=model_name,
            contents=prompt,
            config=generation_config,
        )
        
        return response.text
        
    except Exception as e:
        return f"❌ שגיאה ביצירת תשובה: {str(e)}"

# App header
st.title("🤖 מערכת הפחתת קיטוב פוליטי")
st.markdown("### מערכת שיחה חכמה לדיאלוג פוליטי בנושא מלחמת עזה")
st.markdown("---")

# Sidebar
with st.sidebar:
    st.header("⚙️ מידע על המערכת")
    
    # Model info
    st.info("🧠 **מודל**: gemini-2.5-flash")
    st.info("🌐 **חיפוש ברשת**: פעיל")
    
    # Temperature setting
    temperature = st.slider(
        "🌡️ רמת יצירתיות:",
        min_value=0.0,
        max_value=1.0,
        value=0.7,
        step=0.1,
        help="ערך נמוך = תשובות עקביות יותר, ערך גבוה = תשובות יצירתיות יותר"
    )
    
    st.markdown("---")
    
    # Project info
    st.markdown("**פרויקט גמר MLDS**")
    st.markdown("פיתוח סוכנים שיחתיים להפחתת קיטוב פוליטי")
    
    st.markdown("---")
    
    # Clear history button
    if st.button("🗑️ נקה היסטוריית שיחה", use_container_width=True):
        if "messages" in st.session_state:
            del st.session_state["messages"]
        st.rerun()

# Initialize session state for chat history
if "messages" not in st.session_state:
    st.session_state.messages = []

# Get API key
api_key = get_api_key()

if not api_key:
    st.error("⚠️ שגיאה: מפתח ה-API של Google Gemini לא הוגדר")
    
    with st.expander("הוראות התקנה"):
        st.markdown("""
        **להגדרת המערכת:**
        
        1. **לפריסה ב-Streamlit Cloud:**
           - צור קובץ `.streamlit/secrets.toml`
           - הוסף: `GEMINI_API_KEY = "your_api_key_here"`
        
        2. **לפיתוח מקומי:**
           - צור קובץ `.env` 
           - הוסף: `GEMINI_API_KEY=your_api_key_here`
        
        🔗 [קבל מפתח API חינמי](https://makersuite.google.com/app/apikey)
        """)
else:
    # Display chat history
    for message in st.session_state.messages:
        with st.chat_message(message["role"]):
            st.markdown(
                f'<div style="direction: rtl; text-align: right;">{message["content"]}</div>',
                unsafe_allow_html=True
            )

    # Chat input
    if prompt := st.chat_input("כתוב כאן את השאלה או ההערה שלך בנושא מלחמת עזה..."):
        # Add user message to history
        st.session_state.messages.append({"role": "user", "content": prompt})

        # Display user message
        with st.chat_message("user"):
            st.markdown(
                f'<div style="direction: rtl; text-align: right;">{prompt}</div>', 
                unsafe_allow_html=True
            )

        # Generate and display assistant response
        with st.chat_message("assistant"):
            with st.spinner("🤔 מעבד את השאלה..."):
                response = get_gemini_response(prompt, api_key, temperature=temperature)
                
                st.markdown(
                    f'<div style="direction: rtl; text-align: right;">{response}</div>',
                    unsafe_allow_html=True
                )
                
                # Add assistant message to history
                st.session_state.messages.append({
                    "role": "assistant", 
                    "content": response
                })
