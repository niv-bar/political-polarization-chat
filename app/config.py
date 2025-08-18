"""Application configuration and constants."""

# UI Constants
PARTIES_LIST = [
    "ליכוד", "יש עתיד", "הציונות הדתית", "יהדות התורה",
    "העבודה", "מרץ", "ש״ס", "ישראל ביתנו"
]

DEMOGRAPHIC_OPTIONS = {
    "gender": ["", "זכר", "נקבה", "אחר", "מעדיף/ה לא לענות"],
    "marital_status": ["", "רווק/ה", "נשוי/אה", "גרוש/ה", "אלמן/ה", "בזוגיות"],
    "region": ["", "צפון", "חיפה והצפון", "מרכז", "ירושלים", "דרום", "יהודה ושומרון"],
    "protest_participation": ["", "לא השתתפתי", "השתתפתי מדי פעם", "השתתפתי רבות", "השתתפתי באופן קבוע"]
}

INFLUENCE_SOURCES = [
    "משפחה", "חברים", "מדיה מסורתית", "רשתות חברתיות",
    "פוליטיקאים", "אקדמיה", "דת/מנהיגים רוחניים", "ניסיון אישי"
]

SOCIAL_SITUATIONS = [
    "לחיות באותה השכונה",
    "לעבוד באותה מקום עבודה",
    "להיות חברים קרובים",
    "שבן/בת המשפחה שלי יתחתן עם מישהו מהקבוצה הזו"
]

# App Settings
MAX_PARTICIPANTS = 300
DEFAULT_AGE = 25
MIN_AGE = 18
MAX_AGE = 120

# Firebase Collection Names
CONVERSATIONS_COLLECTION = "conversations"
PROFILES_COLLECTION = "profiles"

# AI Model Settings
GEMINI_MODEL = "gemini-2.5-flash"
AI_TEMPERATURE = 0.7
AI_TOP_P = 0.95
AI_TOP_K = 64
AI_MAX_OUTPUT_TOKENS = 8192