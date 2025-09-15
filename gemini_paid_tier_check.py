import streamlit as st
from google import genai as google_genai
from google.genai import types
import time

def quick_tier_check(api_key: str) -> str:
    """Quick check - returns 'PAID' or 'FREE'."""

    client = google_genai.Client(api_key=api_key)
    count = 0

    # Try 16 rapid requests (more than free tier allows)
    for i in range(16):
        try:
            client.models.generate_content(
                model="gemini-2.0-flash",
                contents="t",
                config=types.GenerateContentConfig(max_output_tokens=1)
            )
            count += 1
            time.sleep(0.2)
        except:
            break

    return "PAID" if count >= 16 else "FREE"


# Usage
api_key = st.secrets.get("GEMINI_API_KEY", "")
tier = quick_tier_check(api_key)
print(f"You are on {tier} tier")