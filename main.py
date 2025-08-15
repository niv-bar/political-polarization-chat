import streamlit as st
import google.generativeai as genai
from google import genai as google_genai
from google.genai import types
import warnings

warnings.filterwarnings("ignore", category=UserWarning, module="tqdm")

# Page configuration
st.set_page_config(
    page_title="AI Assistant (Gemini)",
    page_icon="🤖",
    layout="wide"
)

# Hebrew RTL support CSS
st.markdown("""
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
</style>
""", unsafe_allow_html=True)

st.title("🤖 AI Assistant (Gemini)")
st.markdown("---")

# Sidebar settings
with st.sidebar:
    st.header("⚙️ הגדרות")

    # API key input
    api_key = st.text_input(
        "🔑 Gemini API Key:",
        type="password",
        value=st.session_state.get("api_key", "")
    )
    if api_key:
        st.session_state.api_key = api_key

    model_choice = st.selectbox(
        "בחר מודל:",
        [
            "gemini-2.5-flash",
            "gemini-1.5-pro"
        ],
        index=0
    )

    temperature = st.slider(
        "Temperature (יצירתיות):",
        min_value=0.0,
        max_value=2.0,
        value=0.7,
        step=0.1
    )

    web_search = st.checkbox(
        "🌐 חיפוש ברשת",
        value=False
    )

    st.markdown("---")
    if st.button("🗑️ נקה היסטוריה"):
        st.session_state.messages = []
        st.rerun()

# Chat history
if "messages" not in st.session_state:
    st.session_state.messages = []

# Gemini request function
def get_gemini_response(prompt, api_key, model_name, temp, enable_web_search=False):
    try:
        if enable_web_search:
            client = google_genai.Client(api_key=api_key)
            grounding_tool = types.Tool(google_search=types.GoogleSearch())
            config = types.GenerateContentConfig(
                tools=[grounding_tool],
                temperature=temp,
                top_p=0.95,
                top_k=64,
                max_output_tokens=8192,
            )
            response = client.models.generate_content(
                model=model_name,
                contents=prompt,
                config=config,
            )
            return response.text
        else:
            genai.configure(api_key=api_key)
            generation_config = {
                "temperature": temp,
                "top_p": 0.95,
                "top_k": 64,
                "max_output_tokens": 8192,
            }
            model = genai.GenerativeModel(
                model_name=model_name,
                generation_config=generation_config,
            )
            response = model.generate_content(prompt)
            return response.text
    except Exception as e:
        return f"❌ שגיאה ב-Gemini: {str(e)}"

# Main interface
if not st.session_state.get("api_key"):
    st.warning("⚠️ אנא הזן מפתח API של Google Gemini בצד שמאל.")
    st.info("💡 קבל מפתח API חינמי מ-[Google AI Studio](https://makersuite.google.com/app/apikey)")
else:
    for message in st.session_state.messages:
        with st.chat_message(message["role"]):
            st.markdown(f'<div style="direction: rtl; text-align: right;">{message["content"]}</div>', unsafe_allow_html=True)

    if prompt := st.chat_input("כתב כאן את השאלה או הבקשה שלך..."):
        st.session_state.messages.append({"role": "user", "content": prompt})
        with st.chat_message("user"):
            st.markdown(f'<div style="direction: rtl; text-align: right;">{prompt}</div>', unsafe_allow_html=True)

        with st.chat_message("assistant"):
            with st.spinner("🤔 חושב..."):
                response_text = get_gemini_response(
                    prompt,
                    st.session_state.api_key,
                    model_choice,
                    temperature,
                    web_search
                )
                st.markdown(f'<div style="direction: rtl; text-align: right;">{response_text}</div>', unsafe_allow_html=True)
                st.session_state.messages.append({"role": "assistant", "content": response_text})
