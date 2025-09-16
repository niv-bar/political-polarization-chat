import json
import os
from datetime import datetime
from google import genai as google_genai
from google.genai import types
import time
import random
from pathlib import Path
import toml

# =====================================
# Configuration
# =====================================
current_dir = Path(__file__).parent
parent_dir = current_dir.parent
secrets_path = parent_dir / '.streamlit' / 'secrets.toml'

if secrets_path.exists():
    with open(secrets_path, 'r') as f:
        secrets = toml.load(f)
        API_KEY = secrets.get("GEMINI_API_KEY", "")
else:
    print(f"ERROR: Secrets file not found at: {secrets_path}")
    exit(1)

TEST_MODE = True
MAX_MESSAGES = 20
FAKE_USERS_DIR = "fake_users"
INTERVENTIONS_DIR = "interventions"
OUTPUT_DIR = "conversations"

os.makedirs(FAKE_USERS_DIR, exist_ok=True)
os.makedirs(INTERVENTIONS_DIR, exist_ok=True)
os.makedirs(OUTPUT_DIR, exist_ok=True)

try:
    client = google_genai.Client(api_key=API_KEY)
except Exception as e:
    print(f"ERROR: Failed to initialize Gemini client: {e}")
    exit(1)

import csv  # ✅ חדש

def save_conversation_csv(conversation, filepath_csv):
    """
    שמירת שיחה כ-CSV שבו כל שורה היא זוג הודעות (assistant,user) לפי הסדר.
    אם מספר ההודעות אי-זוגי, ההודעה האחרונה נשמרת לבדה.
    """
    headers = [
        "assistant_content", "assistant_timestamp",
        "user_content",      "user_timestamp"
    ]

    rows = []
    i = 0
    while i < len(conversation):
        msg1 = conversation[i]
        if i + 1 < len(conversation):
            msg2 = conversation[i + 1]
            if msg1["role"] == "assistant":
                a_content, a_time = msg1["content"], msg1["timestamp"]
                u_content, u_time = msg2["content"], msg2["timestamp"]
            else:
                u_content, u_time = msg1["content"], msg1["timestamp"]
                a_content, a_time = msg2["content"], msg2["timestamp"]
            rows.append([a_content, a_time, u_content, u_time])
            i += 2
        else:
            if msg1["role"] == "assistant":
                rows.append([msg1["content"], msg1["timestamp"], "", ""])
            else:
                rows.append(["", "", msg1["content"], msg1["timestamp"]])
            i += 1

    # Add UTF-8 BOM for Excel compatibility
    with open(filepath_csv, 'w', encoding='utf-8-sig', newline='') as f:  # ← Changed here
        writer = csv.writer(f)
        writer.writerow(headers)
        writer.writerows(rows)


def load_fake_user(filename):
    with open(f"{FAKE_USERS_DIR}/{filename}", 'r', encoding='utf-8') as f:
        return f.read()


def load_intervention(filename):
    with open(f"{INTERVENTIONS_DIR}/{filename}", 'r', encoding='utf-8') as f:
        return f.read()


def generate_conversation(fake_user_profile, intervention_prompt, fake_user_name, intervention_name):
    conversation = []
    start_time = datetime.now()
    is_misperception = "misperception" in intervention_name.lower()

    print(f"\n{'=' * 50}")
    print(f"Starting conversation generation")
    print(f"Profile: {fake_user_name}")
    print(f"Intervention: {intervention_name}")
    print(f"Web search: {'Enabled' if is_misperception else 'Disabled'}")
    print(f"{'=' * 50}\n")

    # ✅ פרומפט בסיסי – בקשה מפורשת להחזיר תשובת assistant בלבד
    system_prompt = f"""
אתה משתתף במחקר על שיחות פוליטיות בישראל. 
נהל שיחה טבעית עם ישראלי אחר על המלחמה בעזה.

הפרופיל של הישראלי:
{fake_user_profile}

ההנחיות שלך לשיחה:
{intervention_prompt}

{"חשוב: אתה חייב להשתמש בחיפוש באינטרנט כדי למצוא נתוני סקרים אמיתיים ועדכניים!" if is_misperception else ""}

חוקי השיחה:
1. אתה (המשתתף) פותח את השיחה.
2. השיחה צריכה להיות טבעית וזורמת.
3. מקסימום 20 הודעות (10 מכל צד).
4. סיום טבעי והדרגתי.
5. תגובות קצרות (עד 3 משפטים).
6. עברית פשוטה ויומיומית.

⚠️ החזר *רק* את הטקסט של תגובת המשתתף (assistant) ללא סימון "משתמש" או כל דמות אחרת.
התחל את השיחה עכשיו (אתה פותח):
"""  # ✅ הוספת שורה שמדגישה "רק טקסט של משתתף"

    config = types.GenerateContentConfig(
        tools=[types.Tool(google_search=types.GoogleSearch())] if is_misperception else [],
        temperature=1,
        top_p=0.8,
        top_k=30,
        max_output_tokens=2000,
        candidate_count=1
    )

    current_prompt = system_prompt

    for i in range(MAX_MESSAGES):
        if i % 2 == 0:
            role = "assistant"
            turn = "Participant"
            # ✅ בקשה מפורשת להחזיר תשובת assistant בלבד
            prompt = (
                f"{current_prompt}\n\n"
                f"עכשיו תור המשתתף (אתה) להגיב. "
                f"החזר רק את תשובתך, ללא דיאלוג מדומה של המשתמש."
            )
            if is_misperception and i > 0:
                prompt += "\nאם רלוונטי, חפש נתונים אמיתיים מסקרים עדכניים!"
        else:
            role = "user"
            turn = "Fake User"
            prompt = (
                f"{current_prompt}\n\n"
                f"עכשיו תור הפרופיל להגיב בהתאם לאישיות שלו. "
                f"החזר רק את תשובת הפרופיל, ללא דיאלוג של הצד השני."
            )

        if i >= 14:
            prompt += f"\n\nזה הודעה {i + 1} מתוך 20. אם זה נראה טבעי, התחל לסיים את השיחה בהדרגה."

        print(f"Message {i + 1}/{MAX_MESSAGES} - {turn}'s turn... ", end="", flush=True)

        try:
            response = client.models.generate_content(
                model="gemini-2.0-flash",
                contents=prompt,
                config=config
            )
            message_content = response.text.strip()
            print(f"✓ ({len(message_content.split())} words)")
            preview = message_content[:50] + "..." if len(message_content) > 50 else message_content
            print(f"   Preview: {preview}")
        except Exception as e:
            print(f"✗ Error: {e}")
            raise e

        message = {
            "role": role,
            "content": message_content,
            "timestamp": datetime.now().isoformat()
        }
        conversation.append(message)

        current_prompt += f"\n\n{message_content}"

        ending_phrases = ["להתראות", "ביי", "שיהיה", "נדבר", "תודה על השיחה", "היה נעים", "להשתמע"]
        if any(phrase in message_content for phrase in ending_phrases) and i >= 10:
            print(f"\n→ Natural ending detected at message {i + 1}")
            break

        time.sleep(1)

    end_time = datetime.now()
    duration = (end_time - start_time).total_seconds()

    print(f"\n{'=' * 50}")
    print(f"Conversation completed!")
    print(f"Total messages: {len(conversation)}")
    print(f"Duration: {duration:.1f} seconds")
    print(f"{'=' * 50}\n")

    return {
        "profile_id": fake_user_name.replace(".txt", ""),
        "intervention": intervention_name.replace(".txt", ""),
        "conversation": conversation,
        "metadata": {
            "start_time": start_time.isoformat(),
            "end_time": end_time.isoformat(),
            "total_messages": len(conversation),
            "ending_reason": "natural" if len(conversation) < MAX_MESSAGES else "max_messages",
            "web_search_enabled": is_misperception,
            "duration_seconds": duration
        }
    }


def main():
    fake_users = [f for f in os.listdir(FAKE_USERS_DIR) if f.endswith('.txt')]
    interventions = [f for f in os.listdir(INTERVENTIONS_DIR) if f.endswith('.txt')]

    if not fake_users:
        print(f"ERROR: No .txt files found in {FAKE_USERS_DIR}/")
        return
    if not interventions:
        print(f"ERROR: No .txt files found in {INTERVENTIONS_DIR}/")
        return

    print(f"Found {len(fake_users)} fake users and {len(interventions)} interventions")

    if TEST_MODE:
        selected_user = random.choice(fake_users)
        selected_intervention = random.choice(interventions)
        fake_users = [selected_user]
        interventions = [selected_intervention]
        print(f"\nTEST MODE: Randomly selected → User: {selected_user}, Intervention: {selected_intervention}")
        print("-" * 50)

    for fake_user_file in fake_users:
        try:
            fake_user_profile = load_fake_user(fake_user_file)
        except Exception as e:
            print(f"Error loading fake user {fake_user_file}: {e}")
            continue

        for intervention_file in interventions:
            try:
                intervention_prompt = load_intervention(intervention_file)
            except Exception as e:
                print(f"Error loading intervention {intervention_file}: {e}")
                continue

            try:
                conversation_data = generate_conversation(
                    fake_user_profile,
                    intervention_prompt,
                    fake_user_file,
                    intervention_file
                )
                # Save conversation
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                base_name = f"{timestamp}_{fake_user_file.replace('.txt', '')}_{intervention_file.replace('.txt', '')}"
                json_path = os.path.join(OUTPUT_DIR, f"{base_name}.json")
                csv_path = os.path.join(OUTPUT_DIR, f"{base_name}.csv")  # ✅ חדש

                with open(json_path, 'w', encoding='utf-8') as f:
                    json.dump(conversation_data, f, ensure_ascii=False, indent=2)

                # ✅ שמירת ה-CSV
                save_conversation_csv(conversation_data["conversation"], csv_path)

                print(f"✅ Saved: {base_name}.json and {base_name}.csv")

                if not TEST_MODE:
                    time.sleep(5)
            except Exception as e:
                print(f"❌ Error generating conversation: {e}")
                continue


if __name__ == "__main__":
    main()
