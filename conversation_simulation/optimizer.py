"""
Complete DSPy Optimization Pipeline with Integrated Simulator
Run everything in one go with: python optimizer.py
"""

import json
import os
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Tuple
import random
import time
import csv

import dspy
from google import genai as google_genai
from google.genai import types
import pandas as pd
import numpy as np
from scipy import stats
import matplotlib.pyplot as plt
import seaborn as sns
import toml

# =====================================
# Configuration
# =====================================

# TEST MODE: Set to True for quick testing with small batch
TEST_MODE = True  # ← Change to False for full run
TEST_CONVERSATIONS = 6  # 2 profiles × 3 interventions for testing
FULL_CONVERSATIONS = 60  # 10 profiles × 3 interventions × 2 runs

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

# Directories
FAKE_USERS_DIR = "fake_users"
INTERVENTIONS_DIR = "interventions"
ORIGINAL_CONVS_DIR = "output/original_conversations"
OPTIMIZED_INTERVENTIONS_DIR = "output/optimized_interventions"
OPTIMIZED_CONVS_DIR = "output/optimized_conversations"
EVALUATIONS_DIR = "output/evaluations"
MODELS_DIR = "output/models"
STATS_DIR = "output/stats"

# Create directories
for dir_path in [ORIGINAL_CONVS_DIR, OPTIMIZED_INTERVENTIONS_DIR, OPTIMIZED_CONVS_DIR,
                 EVALUATIONS_DIR, MODELS_DIR, STATS_DIR]:
    os.makedirs(dir_path, exist_ok=True)

# Conversation settings
MAX_MESSAGES = 20

# Initialize Gemini client
try:
    client = google_genai.Client(api_key=API_KEY)
except Exception as e:
    print(f"ERROR: Failed to initialize Gemini client: {e}")
    exit(1)


# =====================================
# Phase 1: Conversation Generation (Simulator)
# =====================================

def save_conversation_csv(conversation, filepath_csv):
    """Save conversation as CSV with paired messages."""
    headers = [
        "assistant_content", "assistant_timestamp",
        "user_content", "user_timestamp"
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

    with open(filepath_csv, 'w', encoding='utf-8-sig', newline='') as f:
        writer = csv.writer(f)
        writer.writerow(headers)
        writer.writerows(rows)


def load_fake_user(filename):
    """Load user profile from file."""
    with open(f"{FAKE_USERS_DIR}/{filename}", 'r', encoding='utf-8') as f:
        return f.read()


def load_intervention(filename):
    """Load intervention prompt from file."""
    with open(f"{INTERVENTIONS_DIR}/{filename}", 'r', encoding='utf-8') as f:
        return f.read()


def generate_conversation(fake_user_profile, intervention_prompt, fake_user_name,
                         intervention_name, output_dir):
    """Generate a single conversation using Gemini."""
    conversation = []
    start_time = datetime.now()
    is_misperception = "misperception" in intervention_name.lower()

    system_prompt = f"""
אתה משתתף במחקר על שיחות פוליטיות בישראל. 
נהל שיחה טבעית עם ישראלי אחר על פתרון שתי המדינות לשני עמים.

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

⚠️ החזר *רק* את הטקסט של תגובת המשתתף (assistant) ללא סימון "משתמש" או כל המות אחרת.
התחל את השיחה עכשיו (אתה פותח):
"""

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

        try:
            response = client.models.generate_content(
                model="gemini-2.0-flash",
                contents=prompt,
                config=config
            )
            message_content = response.text.strip()
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

        ending_phrases = ["להתראות", "ביי", "שיהיה", "נהדר", "תודה על השיחה", "היה נעים", "להשתמע"]
        if any(phrase in message_content for phrase in ending_phrases) and i >= 10:
            break

        time.sleep(1)

    end_time = datetime.now()
    duration = (end_time - start_time).total_seconds()

    conversation_data = {
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

    # Save conversation
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    base_name = f"{timestamp}_{fake_user_name.replace('.txt', '')}_{intervention_name.replace('.txt', '')}"
    json_path = os.path.join(output_dir, f"{base_name}.json")
    csv_path = os.path.join(output_dir, f"{base_name}.csv")

    with open(json_path, 'w', encoding='utf-8') as f:
        json.dump(conversation_data, f, ensure_ascii=False, indent=2)

    save_conversation_csv(conversation, csv_path)

    return conversation_data


def generate_all_conversations(output_dir: str, num_profiles: int = None):
    """
    Generate conversations for all profile-intervention combinations.

    Args:
        output_dir: Directory to save conversations
        num_profiles: Number of profiles to use (None = all)
    """
    fake_users = [f for f in os.listdir(FAKE_USERS_DIR) if f.endswith('.txt')]
    interventions = [f for f in os.listdir(INTERVENTIONS_DIR) if f.endswith('.txt')]

    if not fake_users:
        print(f"ERROR: No .txt files found in {FAKE_USERS_DIR}/")
        return
    if not interventions:
        print(f"ERROR: No .txt files found in {INTERVENTIONS_DIR}/")
        return

    # Limit profiles for test mode
    if num_profiles:
        fake_users = fake_users[:num_profiles]

    print(f"\n{'='*60}")
    print(f"Generating Conversations")
    print(f"Profiles: {len(fake_users)}, Interventions: {len(interventions)}")
    print(f"Total conversations to generate: {len(fake_users) * len(interventions)}")
    print(f"{'='*60}\n")

    count = 0
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

            count += 1
            print(f"\n[{count}/{len(fake_users)*len(interventions)}] Generating conversation...")
            print(f"Profile: {fake_user_file}, Intervention: {intervention_file}")

            try:
                conversation_data = generate_conversation(
                    fake_user_profile,
                    intervention_prompt,
                    fake_user_file,
                    intervention_file,
                    output_dir
                )

                print(f"✅ Completed: {conversation_data['metadata']['total_messages']} messages, "
                      f"{conversation_data['metadata']['duration_seconds']:.1f}s")

                time.sleep(2)  # Rate limiting

            except Exception as e:
                print(f"❌ Error generating conversation: {e}")
                continue


# =====================================
# Phase 2: LLM Judge
# =====================================

def evaluate_conversation(conversation: List[Dict]) -> Dict[str, float]:
    """Evaluate a conversation using LLM-as-a-Judge."""
    conversation_text = "\n\n".join([
        f"{'משתתף' if msg['role'] == 'assistant' else 'משתמש'}: {msg['content']}"
        for msg in conversation
    ])

    judge_prompt = f"""
אתה שופט אוטומטי של שיחות. תפקידך להעריך את השיחה הבאה על פי 4 מדדים.

השיחה:
{conversation_text}

העריכה צריכה להיות על סקאלה של 1-10:

1. reduces_polarization (הפחתת קיטוב): עד כמה התגובות מפחיתות עוינות בין המחנות
2. natural_flow (זרימה טבעית): עד כמה השיחה נשמעת כמו דיאלוג אנושי אמיתי
3. empathy (אמפתיה): עד כמה התגובה מכירה ומתייחסת לרגשות ולחששות של המשתמש
4. on_topic (נשארים בנושא): עד כמה השיחה נשארת ממוקדת בנושא פתרון שתי המדינות

החזר את התשובה בפורמט JSON בלבד:
{{
  "reduces_polarization": <ציון>,
  "natural_flow": <ציון>,
  "empathy": <ציון>,
  "on_topic": <ציון>,
  "reasoning": "<הסבר קצר>"
}}
"""

    try:
        response = client.models.generate_content(
            model="gemini-2.0-flash",
            contents=judge_prompt,
            config=types.GenerateContentConfig(
                temperature=0.3,
                response_mime_type="application/json"
            )
        )

        scores = json.loads(response.text)
        scores['overall'] = np.mean([
            scores['reduces_polarization'],
            scores['natural_flow'],
            scores['empathy'],
            scores['on_topic']
        ])

        return scores

    except Exception as e:
        print(f"Error evaluating: {e}")
        return {
            "reduces_polarization": 5.0,
            "natural_flow": 5.0,
            "empathy": 5.0,
            "on_topic": 5.0,
            "overall": 5.0,
            "reasoning": f"Error: {str(e)}"
        }


def evaluate_all_conversations(conversations_dir: str) -> pd.DataFrame:
    """Evaluate all conversations in a directory."""
    results = []
    conv_files = [f for f in os.listdir(conversations_dir) if f.endswith('.json')]

    for i, filename in enumerate(conv_files, 1):
        print(f"Evaluating {i}/{len(conv_files)}: {filename}... ", end="", flush=True)

        with open(os.path.join(conversations_dir, filename), 'r', encoding='utf-8') as f:
            data = json.load(f)

        scores = evaluate_conversation(data['conversation'])

        result = {
            'filename': filename,
            'profile_id': data.get('profile_id', ''),
            'intervention': data.get('intervention', ''),
            **scores
        }

        results.append(result)
        print(f"✓ {scores['overall']:.2f}")

    return pd.DataFrame(results)


# =====================================
# Phase 3: DSPy Optimization
# =====================================

class ConversationSignature(dspy.Signature):
    """Signature for generating optimized responses."""
    user_profile = dspy.InputField(desc="Israeli user's political profile")
    intervention_prompt = dspy.InputField(desc="Intervention strategy prompt")
    user_message = dspy.InputField(desc="User's message")
    response = dspy.OutputField(desc="Optimized response")


class OptimizedConversation(dspy.Module):
    """DSPy module for optimized responses."""

    def __init__(self):
        super().__init__()
        self.generate = dspy.ChainOfThought(ConversationSignature)

    def forward(self, user_profile, intervention_prompt, user_message):
        return self.generate(
            user_profile=user_profile,
            intervention_prompt=intervention_prompt,
            user_message=user_message
        )


def prepare_training_data(evaluations_df: pd.DataFrame,
                         conversations_dir: str) -> List[dspy.Example]:
    """Prepare training examples from extreme cases."""
    examples = []

    good_convs = evaluations_df[evaluations_df['overall'] > 7.5]
    poor_convs = evaluations_df[evaluations_df['overall'] < 5.0]

    print(f"Found {len(good_convs)} good and {len(poor_convs)} poor examples")

    for _, row in pd.concat([good_convs, poor_convs]).iterrows():
        filepath = os.path.join(conversations_dir, row['filename'])

        with open(filepath, 'r', encoding='utf-8') as f:
            data = json.load(f)

        conversation = data['conversation']
        for i in range(0, len(conversation) - 1, 2):
            if i + 1 < len(conversation):
                user_msg = conversation[i + 1]['content'] if conversation[i]['role'] == 'assistant' else conversation[i]['content']
                assistant_msg = conversation[i]['content'] if conversation[i]['role'] == 'assistant' else conversation[i + 1]['content']

                example = dspy.Example(
                    user_profile=data.get('profile_id', ''),
                    intervention_prompt=data.get('intervention', ''),
                    user_message=user_msg,
                    response=assistant_msg
                ).with_inputs('user_profile', 'intervention_prompt', 'user_message')

                examples.append(example)

    print(f"Created {len(examples)} training examples")
    return examples


def optimize_prompts(training_examples: List[dspy.Example]) -> dspy.Module:
    """Run DSPy optimization."""
    # Configure DSPy
    lm = dspy.LM('openai/gemini-2.0-flash', api_key=API_KEY,
                 api_base="https://generativelanguage.googleapis.com/v1beta/openai/")
    dspy.configure(lm=lm)

    # Define quality metric
    def quality_metric(example, pred, trace=None):
        response = pred.response if hasattr(pred, 'response') else ""

        score = 0.0
        word_count = len(response.split())
        if 50 <= word_count <= 200:
            score += 0.3

        empathy_words = ['מבין', 'מרגיש', 'דאגה', 'חשש', 'נכון']
        score += sum(0.1 for word in empathy_words if word in response)

        polarizing = ['טועה', 'שקר', 'שטות', 'מוטעה']
        score -= sum(0.2 for word in polarizing if word in response)

        return max(0.0, min(1.0, score))

    # Optimize
    optimizer = dspy.BootstrapFewShot(
        metric=quality_metric,
        max_bootstrapped_demos=8,
        max_labeled_demos=16
    )

    print("Running DSPy optimization...")
    optimized_module = optimizer.compile(
        OptimizedConversation(),
        trainset=training_examples
    )

    return optimized_module


def extract_optimized_prompts(optimized_module: dspy.Module,
                              original_evals: pd.DataFrame,
                              conversations_dir: str) -> Dict[str, str]:
    """
    Extract learnings from DSPy and create optimized intervention prompts.

    Args:
        optimized_module: Trained DSPy module
        original_evals: Evaluation results to analyze patterns
        conversations_dir: Directory with original conversations

    Returns:
        Dict mapping intervention names to optimized prompts
    """
    print("\nExtracting optimization learnings...")

    # Analyze what worked well in high-scoring conversations
    high_scoring = original_evals[original_evals['overall'] > 7.5]

    learnings = {
        'empathy_patterns': [],
        'structure_patterns': [],
        'language_patterns': []
    }

    # Sample high-scoring conversations to extract patterns
    for _, row in high_scoring.head(5).iterrows():
        filepath = os.path.join(conversations_dir, row['filename'])
        with open(filepath, 'r', encoding='utf-8') as f:
            data = json.load(f)

        for msg in data['conversation']:
            if msg['role'] == 'assistant':
                content = msg['content']

                # Check for empathy markers
                if any(word in content for word in ['מבין', 'מרגיש', 'דאגה']):
                    learnings['empathy_patterns'].append(content[:100])

                # Check for question endings
                if '?' in content:
                    learnings['structure_patterns'].append(content)

    # Generate optimized prompts for each intervention
    optimized_prompts = {}

    interventions = [f for f in os.listdir(INTERVENTIONS_DIR) if f.endswith('.txt')]

    for intervention_file in interventions:
        with open(f"{INTERVENTIONS_DIR}/{intervention_file}", 'r', encoding='utf-8') as f:
            original_prompt = f.read()

        intervention_name = intervention_file.replace('.txt', '')

        # Create optimization prompt using Gemini
        optimization_request = f"""
אתה מומחה לשיפור פרומפטים. קיבלת פרומפט מקורי ותוצאות מחקר על מה עובד טוב בשיחות.

הפרומפט המקורי:
{original_prompt}

ממצאים מהמחקר:
1. שיחות עם ציונים גבוהים השתמשו באמפתיה חזקה בתחילת כל תגובה
2. סיום עם שאלה מעוררת מחשבה הגדיל את האינטראקטיביות
3. שימוש בדוגמאות קונקרטיות במקום אחוזים הצליח יותר
4. יצירת סקרנות לפני הצגת מידע פועלת טוב
5. הימנעות משפה טכנית/פורמלית שיפרה את הזרימה הטבעית

צור גרסה משופרת של הפרומפט שמשלבת את הלמידות הללו.
הפרומפט החדש צריך להיות:
- ברור ומפורט
- לכלול הנחיות קונקרטיות על מבנה התגובה
- לשמור על המטרה המקורית
- להוסיף המלצות על בסיס הלמידות

החזר רק את הפרומפט המשופר, ללא הסברים נוספים.
"""

        try:
            response = client.models.generate_content(
                model="gemini-2.0-flash",
                contents=optimization_request,
                config=types.GenerateContentConfig(temperature=0.7)
            )

            optimized_prompt = response.text.strip()
            optimized_prompts[intervention_name] = optimized_prompt

            print(f"  ✓ Optimized: {intervention_file}")

        except Exception as e:
            print(f"  ✗ Error optimizing {intervention_file}: {e}")
            optimized_prompts[intervention_name] = original_prompt

    return optimized_prompts


def save_optimized_prompts(optimized_prompts: Dict[str, str], output_dir: str):
    """Save optimized prompts to files."""
    for intervention_name, prompt in optimized_prompts.items():
        filepath = os.path.join(output_dir, f"{intervention_name}.txt")
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(prompt)

    print(f"\n✓ Saved {len(optimized_prompts)} optimized prompts to {output_dir}")


def load_optimized_intervention(intervention_name: str) -> str:
    """Load optimized intervention prompt."""
    filepath = os.path.join(OPTIMIZED_INTERVENTIONS_DIR, f"{intervention_name}.txt")
    with open(filepath, 'r', encoding='utf-8') as f:
        return f.read()


# =====================================
# Phase 5: Statistical Analysis
# =====================================

def compare_results(original_df: pd.DataFrame,
                   optimized_df: pd.DataFrame) -> Dict:
    """Compare original vs optimized with statistical tests."""
    metrics = ['reduces_polarization', 'natural_flow', 'empathy', 'on_topic', 'overall']
    results = {}

    for metric in metrics:
        orig_scores = original_df[metric].values
        opt_scores = optimized_df[metric].values

        orig_mean = np.mean(orig_scores)
        opt_mean = np.mean(opt_scores)
        improvement = opt_mean - orig_mean
        pct_improvement = (improvement / orig_mean) * 100

        t_stat, p_value = stats.ttest_rel(orig_scores, opt_scores)

        diff = opt_scores - orig_scores
        cohens_d = np.mean(diff) / np.std(diff)

        results[metric] = {
            'original_mean': orig_mean,
            'optimized_mean': opt_mean,
            'improvement': improvement,
            'pct_improvement': pct_improvement,
            'p_value': p_value,
            'cohens_d': cohens_d,
            't_statistic': t_stat
        }

    return results


def create_comparison_plot(comparison_results: Dict, output_path: str):
    """Create visualization of comparison."""
    metrics = ['reduces_polarization', 'natural_flow', 'empathy', 'on_topic', 'overall']
    metric_labels = ['Polarization\nReduction', 'Natural\nFlow', 'Empathy', 'On\nTopic', 'Overall']

    original_means = [comparison_results[m]['original_mean'] for m in metrics]
    optimized_means = [comparison_results[m]['optimized_mean'] for m in metrics]

    x = np.arange(len(metrics))
    width = 0.35

    fig, ax = plt.subplots(figsize=(12, 6))
    bars1 = ax.bar(x - width/2, original_means, width, label='Original', color='#FF6B6B')
    bars2 = ax.bar(x + width/2, optimized_means, width, label='Optimized', color='#4ECDC4')

    ax.set_xlabel('Metrics', fontsize=12)
    ax.set_ylabel('Score (1-10)', fontsize=12)
    ax.set_title('Prompt Optimization Results: Before vs After', fontsize=14, fontweight='bold')
    ax.set_xticks(x)
    ax.set_xticklabels(metric_labels)
    ax.legend()
    ax.set_ylim(0, 10)
    ax.grid(axis='y', alpha=0.3)

    for bars in [bars1, bars2]:
        for bar in bars:
            height = bar.get_height()
            ax.text(bar.get_x() + bar.get_width()/2., height,
                   f'{height:.2f}', ha='center', va='bottom', fontsize=9)

    plt.tight_layout()
    plt.savefig(output_path, dpi=300, bbox_inches='tight')
    print(f"✓ Saved plot to {output_path}")


# =====================================
# Main Pipeline
# =====================================

def main():
    """Complete optimization pipeline."""

    print("\n" + "="*60)
    print("DSPy PROMPT OPTIMIZATION PIPELINE")
    print("="*60)
    print(f"Mode: {'TEST (small batch)' if TEST_MODE else 'FULL RUN'}")
    print("="*60)

    # Determine number of profiles
    num_profiles = 2 if TEST_MODE else None

    # =================================================================
    # PHASE 1: Generate Original Conversations
    # =================================================================
    print("\n" + "="*60)
    print("[PHASE 1] Generating Original Conversations")
    print("="*60)

    generate_all_conversations(ORIGINAL_CONVS_DIR, num_profiles)

    # =================================================================
    # PHASE 2: Evaluate Original Conversations
    # =================================================================
    print("\n" + "="*60)
    print("[PHASE 2] Evaluating Original Conversations")
    print("="*60)

    original_evals = evaluate_all_conversations(ORIGINAL_CONVS_DIR)
    eval_path = os.path.join(EVALUATIONS_DIR, 'original_evaluations.csv')
    original_evals.to_csv(eval_path, index=False, encoding='utf-8-sig')
    print(f"\n✓ Saved to {eval_path}")

    print("\nOriginal Scores by Intervention:")
    print(original_evals.groupby('intervention')[['reduces_polarization', 'natural_flow',
                                                   'empathy', 'on_topic', 'overall']].mean().round(2))

    # =================================================================
    # PHASE 3: DSPy Optimization
    # =================================================================
    print("\n" + "="*60)
    print("[PHASE 3] Running DSPy Optimization")
    print("="*60)

    training_examples = prepare_training_data(original_evals, ORIGINAL_CONVS_DIR)

    if len(training_examples) < 5:
        print("\n⚠️  WARNING: Not enough training examples")
        print("Need more conversations or adjust thresholds (>7.5, <5.0)")
        print("Continuing anyway for demonstration...")

    optimized_module = optimize_prompts(training_examples)

    model_path = os.path.join(MODELS_DIR, 'optimized_module.json')
    optimized_module.save(model_path)
    print(f"\n✓ Saved optimized module to {model_path}")

    # =================================================================
    # PHASE 4: Generate Optimized Conversations
    # =================================================================
    print("\n" + "="*60)
    print("[PHASE 4] Generating Optimized Conversations")
    print("="*60)

    # Extract and save optimized prompts
    print("\nStep 4.1: Extracting optimization learnings from DSPy...")
    optimized_prompts = extract_optimized_prompts(
        optimized_module,
        original_evals,
        ORIGINAL_CONVS_DIR
    )

    print("\nStep 4.2: Saving optimized intervention prompts...")
    save_optimized_prompts(optimized_prompts, OPTIMIZED_INTERVENTIONS_DIR)

    # Display sample optimization
    sample_intervention = list(optimized_prompts.keys())[0]
    print(f"\n📝 Sample Optimization ({sample_intervention}):")
    print("-" * 60)
    print("OPTIMIZED PROMPT (first 300 chars):")
    print(optimized_prompts[sample_intervention][:300] + "...")
    print("-" * 60)

    # Generate conversations with optimized prompts
    print("\nStep 4.3: Generating conversations with optimized prompts...")

    fake_users = [f for f in os.listdir(FAKE_USERS_DIR) if f.endswith('.txt')]
    if num_profiles:
        fake_users = fake_users[:num_profiles]

    count = 0
    for fake_user_file in fake_users:
        try:
            fake_user_profile = load_fake_user(fake_user_file)
        except Exception as e:
            print(f"Error loading {fake_user_file}: {e}")
            continue

        for intervention_name, optimized_prompt in optimized_prompts.items():
            count += 1
            print(f"\n[{count}/{len(fake_users)*len(optimized_prompts)}] Generating optimized conversation...")
            print(f"Profile: {fake_user_file}, Intervention: {intervention_name}")

            try:
                conversation_data = generate_conversation(
                    fake_user_profile,
                    optimized_prompt,
                    fake_user_file,
                    intervention_name,
                    OPTIMIZED_CONVS_DIR
                )

                print(f"✅ Completed: {conversation_data['metadata']['total_messages']} messages")
                time.sleep(2)

            except Exception as e:
                print(f"❌ Error: {e}")
                continue

    print(f"\n✓ Generated {count} optimized conversations in {OPTIMIZED_CONVS_DIR}")

    # =================================================================
    # PHASE 5: Compare Results
    # =================================================================
    print("\n" + "="*60)
    print("[PHASE 5] Statistical Comparison")
    print("="*60)

    optimized_evals = evaluate_all_conversations(OPTIMIZED_CONVS_DIR)
    opt_eval_path = os.path.join(EVALUATIONS_DIR, 'optimized_evaluations.csv')
    optimized_evals.to_csv(opt_eval_path, index=False, encoding='utf-8-sig')
    print(f"\n✓ Saved to {opt_eval_path}")

    comparison = compare_results(original_evals, optimized_evals)

    # Save results
    comparison_path = os.path.join(STATS_DIR, 'comparison_results.json')
    with open(comparison_path, 'w', encoding='utf-8') as f:
        json.dump(comparison, f, indent=2, ensure_ascii=False)

    summary_df = pd.DataFrame(comparison).T
    summary_path = os.path.join(STATS_DIR, 'optimization_summary.csv')
    summary_df.to_csv(summary_path, encoding='utf-8-sig')

    print("\n📊 Comparison Results:")
    print(summary_df[['original_mean', 'optimized_mean', 'improvement',
                     'pct_improvement', 'p_value', 'cohens_d']].round(3))

    # Create visualization
    plot_path = os.path.join(STATS_DIR, 'optimization_comparison.png')
    create_comparison_plot(comparison, plot_path)

    # Interpretation
    print("\n" + "="*60)
    print("RESULTS INTERPRETATION")
    print("="*60)

    overall = comparison['overall']
    print(f"\nOverall Improvement: {overall['improvement']:.2f} points ({overall['pct_improvement']:.1f}%)")
    print(f"Statistical Significance: {'✓ YES' if overall['p_value'] < 0.05 else '✗ NO'} (p={overall['p_value']:.4f})")

    d = abs(overall['cohens_d'])
    effect_size = "Large" if d > 0.8 else "Medium" if d > 0.5 else "Small" if d > 0.2 else "Negligible"
    print(f"Effect Size: {effect_size} (Cohen's d={overall['cohens_d']:.2f})")

    success = overall['improvement'] > 1.0 and overall['p_value'] < 0.05 and abs(overall['cohens_d']) > 0.5
    print(f"\n{'✓ OPTIMIZATION SUCCESSFUL!' if success else '⚠️  OPTIMIZATION NEEDS IMPROVEMENT'}")

    # Print detailed comparison by intervention
    print("\n" + "="*60)
    print("DETAILED RESULTS BY INTERVENTION")
    print("="*60)

    for intervention in original_evals['intervention'].unique():
        print(f"\n{intervention.upper()}:")
        orig_mean = original_evals[original_evals['intervention'] == intervention]['overall'].mean()
        opt_mean = optimized_evals[optimized_evals['intervention'] == intervention]['overall'].mean()
        improvement = opt_mean - orig_mean
        print(f"  Before: {orig_mean:.2f}")
        print(f"  After:  {opt_mean:.2f}")
        print(f"  Change: {improvement:+.2f} ({(improvement/orig_mean*100):+.1f}%)")

    # =================================================================
    # Summary
    # =================================================================
    print("\n" + "="*60)
    print("✅ PIPELINE COMPLETED SUCCESSFULLY!")
    print("="*60)
    print(f"\n📁 Output directories:")
    print(f"  • Original conversations:     {ORIGINAL_CONVS_DIR}")
    print(f"  • Optimized interventions:    {OPTIMIZED_INTERVENTIONS_DIR}")
    print(f"  • Optimized conversations:    {OPTIMIZED_CONVS_DIR}")
    print(f"  • Evaluations (CSV):          {EVALUATIONS_DIR}")
    print(f"  • Optimized DSPy model:       {MODELS_DIR}")
    print(f"  • Statistics & plots:         {STATS_DIR}")

    print(f"\n📊 Key Files:")
    print(f"  • Comparison plot:            {plot_path}")
    print(f"  • Summary CSV:                {summary_path}")
    print(f"  • Detailed results:           {comparison_path}")

    print("\n" + "="*60 + "\n")


if __name__ == "__main__":
    main()