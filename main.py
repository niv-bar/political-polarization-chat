import streamlit as st
import google.generativeai as genai
from google import genai as google_genai
from google.genai import types
import warnings

# Suppress tqdm warning
warnings.filterwarnings("ignore", category=UserWarning, module="tqdm")

# API Keys - Enter your keys here
GEMINI_API_KEY = "REDACTED_KEY"
OPENAI_API_KEY = "REDACTED_KEY"

# Page configuration
st.set_page_config(
    page_title="AI Assistant",
    page_icon="🤖",
    layout="wide"
)

# Hebrew RTL support CSS
st.markdown("""
<style>
    .main .block-container {
        direction: rtl;
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

    /* Keep sidebar LTR for controls */
    .css-1d391kg {
        direction: ltr;
    }

    /* RTL for chat input */
    .stChatInputContainer {
        direction: rtl;
    }

    .stChatInputContainer input {
        direction: rtl;
        text-align: right !important;
    }

    /* Additional chat input styling */
    div[data-testid="stChatInput"] {
        direction: rtl;
    }

    div[data-testid="stChatInput"] input {
        direction: rtl;
        text-align: right !important;
    }

    /* Chat input placeholder */
    div[data-testid="stChatInput"] input::placeholder {
        text-align: right;
        direction: rtl;
    }
</style>
""", unsafe_allow_html=True)

st.title("🤖 AI Assistant (Gemini + ChatGPT)")
st.markdown("---")

# Sidebar for API keys and settings
with st.sidebar:
    st.header("⚙️ הגדרות")

    # Model selection - only two models
    model_choice = st.selectbox(
        "בחר מודל:",
        [
            "gemini-2.5-flash",
            "gpt-4o-mini"
        ],
        index=0
    )

    st.markdown("---")

    # Temperature setting
    temperature = st.slider(
        "Temperature (יצירתיות):",
        min_value=0.0,
        max_value=2.0,
        value=0.7,
        step=0.1,
        help="ערך נמוך = תשובות יותר עקביות, ערך גבוה = תשובות יותר יצירתיות"
    )

    # Web search setting for Gemini (only show for gemini models)
    if model_choice.startswith("gemini"):
        web_search = st.checkbox(
            "🌐 חיפוש ברשת",
            value=False,
            help="אפשר לחיפוש ברשת עבור תשובות מעודכנות"
        )

    # Max tokens for OpenAI models
    if not model_choice.startswith("gemini"):
        max_tokens = st.slider(
            "Max Tokens:",
            min_value=100,
            max_value=4000,
            value=2000,
            step=100,
            help="מספר מילים מקסימלי בתשובה"
        )

    st.markdown("---")
    if st.button("🗑️ נקה היסטוריה"):
        if "messages" in st.session_state:
            del st.session_state["messages"]
        st.rerun()

# Initialize session state for chat history
if "messages" not in st.session_state:
    st.session_state.messages = []


# Function to get response from Gemini
def get_gemini_response(prompt, api_key, model_name, temp, enable_web_search=False):
    try:
        if enable_web_search:
            # Use the new Google GenAI client for web search
            client = google_genai.Client(api_key=api_key)

            # Define the grounding tool
            grounding_tool = types.Tool(
                google_search=types.GoogleSearch()
            )

            # Configure generation settings
            config = types.GenerateContentConfig(
                tools=[grounding_tool],
                temperature=temp,
                top_p=0.95,
                top_k=64,
                max_output_tokens=8192,
            )

            # Make the request with grounding
            response = client.models.generate_content(
                model=model_name,
                contents=prompt,
                config=config,
            )

            return response.text
        else:
            # Use the legacy API for regular responses
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


# Function to get response from OpenAI
def get_openai_response(prompt, api_key, model_name, temp, max_tok):
    try:
        client = OpenAI(api_key=api_key)

        response = client.chat.completions.create(
            model=model_name,
            messages=[{"role": "user", "content": prompt}],
            temperature=temp,
            max_tokens=max_tok
        )

        return response.choices[0].message.content
    except Exception as e:
        return f"❌ שגיאה ב-OpenAI: {str(e)}"


# Main chat interface
current_api_key = GEMINI_API_KEY if model_choice.startswith("gemini") else OPENAI_API_KEY

if not current_api_key or current_api_key == "your_gemini_api_key_here" or current_api_key == "your_openai_api_key_here":
    provider = "Google Gemini" if model_choice.startswith("gemini") else "OpenAI"
    st.warning(f"⚠️ אנא עדכן את מפתח ה-API של {provider} בקוד")

    if model_choice.startswith("gemini"):
        st.info("💡 קבל מפתח API חינמי מ-[Google AI Studio](https://makersuite.google.com/app/apikey)")
    else:
        st.info("💡 קבל מפתח API מ-[OpenAI Platform](https://platform.openai.com/api-keys)")
else:
    # Display chat history
    for message in st.session_state.messages:
        with st.chat_message(message["role"]):
            if message["role"] == "user":
                st.markdown(f'<div style="direction: rtl; text-align: right;">{message["content"]}</div>',
                            unsafe_allow_html=True)
            else:
                st.markdown(f'<div style="direction: rtl; text-align: right;">{message["content"]}</div>',
                            unsafe_allow_html=True)

    # Chat input
    if prompt := st.chat_input("כתב כאן את השאלה או הבקשה שלך..."):
        # Add user message to history
        st.session_state.messages.append({"role": "user", "content": prompt})

        # Display user message
        with st.chat_message("user"):
            st.markdown(f'<div style="direction: rtl; text-align: right;">{prompt}</div>', unsafe_allow_html=True)

        # Generate and display assistant response
        with st.chat_message("assistant"):
            with st.spinner("🤔 חושב..."):

                if model_choice.startswith("gemini"):
                    response_text = get_gemini_response(
                        prompt,
                        current_api_key,
                        model_choice,
                        temperature,
                        web_search if 'web_search' in locals() else False
                    )
                else:
                    response_text = get_openai_response(prompt, current_api_key, model_choice, temperature, max_tokens)

                st.markdown(f'<div style="direction: rtl; text-align: right;">{response_text}</div>',
                            unsafe_allow_html=True)

                # Add assistant message to history
                st.session_state.messages.append({
                    "role": "assistant",
                    "content": response_text
                })