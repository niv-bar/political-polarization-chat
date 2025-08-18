"""
Political Chatbot Application
Main entry point for the Streamlit app.
"""

import warnings
from app import PoliticalChatbotApp

# Suppress warnings
warnings.filterwarnings("ignore", category=UserWarning, module="tqdm")

def main() -> None:
    """Application entry point."""
    app = PoliticalChatbotApp()
    app.run()

if __name__ == "__main__":
    main()