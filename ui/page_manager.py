import streamlit as st
from typing import Optional, List, Dict, Any
from datetime import datetime
from dataclasses import asdict
import random
from models import UserProfile, ChatMessage
from services import DataService, AIService
from utils import DataExporter
from .ui_components import UIComponents


class PageManager:
    """Handles all page rendering in one class."""

    def __init__(self, data_service: DataService, ai_service: Optional[AIService] = None):
        self.data_service = data_service
        self.ai_service = ai_service
        self.ui = UIComponents()

    def render_main_menu(self) -> None:
        """Render the main menu with user and admin options."""
        self.ui.render_header(title="🔬 מחקר אקדמי על דעות ועמדות בחברה הישראלית",
                              description="""
                              
            

**אודות המחקר:**

* המחקר נערך לטובת מחקר אקדמי ומטרתו להבין טוב יותר את מגוון הדעות בחברה הישראלית
* ההשתתפות היא וולונטרית ואנונימית לחלוטין
* הנתונים ישמשו אך ורק למטרות מחקר אקדמי
* אין תשובות נכונות או שגויות - רק דעתכם האישית חשובה



**מבנה המחקר:**
1. שאלון רקע קצר
2. שיחה חופשית עם מערכת בינה מלאכותית
3. שאלון קצר נוסף לסיכום

תודה על נכונותכם להשתתף במחקר זה!

""")

        col1, col2, col3 = st.columns([1, 2, 1])

        with col2:
            st.markdown("### בחירת נתיב:")

            # User path
            st.markdown("#### 👥 משתתף במחקר")
            if st.button("🚀 התחל השתתפות במחקר", use_container_width=True, type="primary"):
                st.session_state.app_mode = "user"
                st.rerun()

            st.markdown("---")

            # Admin path
            st.markdown("#### 🔒 חוקרים")
            admin_password = st.text_input("סיסמת חוקרים:", type="password", placeholder="סיסמה...")

            if st.button("🔓 כניסה למערכת החוקרים", use_container_width=True):
                if self._verify_admin_password(admin_password):
                    st.session_state.app_mode = "admin"
                    st.session_state.admin_authenticated = True
                    st.success("✅ כניסה מוצלחת")
                    st.rerun()
                else:
                    st.error("❌ סיסמה שגויה")

        self.ui.render_footer()

    def render_questionnaire(self) -> bool:
        """Render unbiased opening questionnaire."""
        self.ui.render_header("📋 שאלון רקע דמוגרפי וחברתי",
                              "שלב ראשון: מידע כללי",
                              """כדי להבין טוב יותר את הרקע החברתי של המשתתפים במחקר, נבקש לענות על כמה שאלות בסיסיות.
""")

        existing_profile = st.session_state.get("temp_user_profile")

        with st.form("user_questionnaire"):
            profile_data = self._render_questionnaire_form(existing_profile)

            skip_validation = st.checkbox("דלג על שדות שלא מולאו",
                                              help="באפשרותך להמשיך גם מבלי למלא את כל השדות")

            submitted = st.form_submit_button("← המשך לשיחה", use_container_width=True, type="primary")

            if submitted:
                if self._validate_questionnaire(profile_data, skip_validation):
                    user_profile = self._create_user_profile(profile_data, existing_profile)
                    self._save_temp_user_profile(user_profile)
                    st.success("תודה על מילוי השאלון! עובר לשיחה...")
                    st.rerun()
                    return True

        # Navigation
        if st.button("→ חזרה לדף הבית", use_container_width=True):
            st.session_state.app_mode = "main_menu"
            st.rerun()

        return False

    def render_chat_interface(self) -> None:
        """Render the main chat interface."""
        self.ui.render_header("💬 שיחה חופשית",
                              "שלב שני: דיאלוג פתוח",
                              "כעת תוכלו לנהל שיחה חופשית על נושאים שונים. השיחה תימשך כ-10-15 דקות.")
        self._render_sidebar()

        if not self.ai_service:
            st.error("❌ שירות הבינה המלאכותית אינו זמין כעת")
            return

        # Add initial message if no conversation yet
        messages = st.session_state.get("messages", [])
        if not messages:
            with st.chat_message("assistant"):
                self.ui.render_rtl_message("""שלום! אני כאן כדי לנהל איתך שיחה על נושאים שונים בחברה הישראלית. 

תוכל לשאול אותי על כל נושא שמעניין אותך - פוליטיקה, חברה, כלכלה, או כל דבר אחר. 
המטרה היא לנהל שיחה פתוחה וכנה.

על מה תרצה לדבר?""")

        # Render chat history
        self._render_chat_history()

        # Handle user input
        if prompt := st.chat_input("כתוב הודעה..."):
            self._handle_user_input(prompt)

    def render_post_chat_questionnaire(self) -> None:
        """Render post-chat questionnaire to measure attitude changes."""
        self.ui.render_header("📊 שאלון סיכום",
                              "שלב שלישי: שאלון סיום",
                              """לאחר השיחה, נבקש לענות על כמה שאלות קצרות נוספות.""")

        existing_profile = st.session_state.get("temp_user_profile")
        if not existing_profile:
            st.error("שגיאה: לא נמצא מידע על המשתתף")
            return

        # הסרנו את הטופס (form) - עכשיו הכל בחוץ
        post_data = self._render_post_chat_form(existing_profile)

        # עדכון הפרופיל בזמן אמת בכל שינוי
        self._update_profile_with_post_data(existing_profile, post_data)
        self._calculate_attitude_changes(existing_profile)
        st.session_state.temp_user_profile = existing_profile

        # הצגת הכפתורים ישירות
        st.markdown("### 🔒 שמירת נתוני המחקר")

        col1, col2 = st.columns(2)
        with col1:
            if st.button("🔁 השתתפות נוספת", use_container_width=True):
                self._reset_application()

        with col2:
            if st.button("💾 אני מסכים לשמור את הנתונים למחקר", use_container_width=True, type="primary"):
                if self._save_conversation_data():
                    st.success("✅ הנתונים נשמרו בהצלחה! תודה רבה על תרומתך למחקר.")
                    st.balloons()


    def _render_questionnaire_form(self, existing_profile: Optional[UserProfile]) -> Dict[str, Any]:
        """Render unbiased questionnaire form."""

        # Section 1: Basic Demographics (neutral presentation)
        st.markdown("### 👤 מידע בסיסי")
        st.caption("מידע דמוגרפי בסיסי לצורך ניתוח המחקר")

        col1, col2 = st.columns(2)

        with col1:
            age = st.number_input("גיל:", min_value=18, max_value=120,
                                  value=existing_profile.age if existing_profile and existing_profile.age > 0 else 30)

            gender = st.selectbox(
                "מגדר:",
                options=["בחר תשובה", "זכר", "נקבה", "אחר"],
                index=self.ui.get_selectbox_index(["בחר תשובה", "זכר", "נקבה", "אחר"],
                                                  existing_profile.gender if existing_profile else "בחר תשובה")
            )

        with col2:
            region = st.selectbox(
                "אזור מגורים:",
                options=["בחר תשובה", "צפון", "חיפה והכרמל", "השרון", "גוש דן", "ירושלים", "השפלה",
                         "דרום", "יהודה ושומרון"],
                index=self.ui.get_selectbox_index(["בחר תשובה", "צפון", "חיפה והקרמל", "השרון",
                                                   "גוש דן", "ירושלים", "השפלה", "דרום", "יהודה ושומרון"],
                                                  existing_profile.region if existing_profile else "בחר תשובה")
            )

            marital_status = st.selectbox(
                "מצב משפחתי:",
                options=["בחר תשובה", "רווק", "נשוי/בזוגיות", "גרוש", "אלמן"],
                index=self.ui.get_selectbox_index(["בחר תשובה", "רווק", "נשוי/בזוגיות", "גרוש", "אלמן"],
                                                  existing_profile.marital_status if existing_profile else "בחר תשובה")
            )

        education = st.selectbox(
            "השכלה:",
            options=["בחר תשובה", "תיכון", "הכשרה מקצועית", "תואר ראשון",
                     "תואר שני", "תואר שלישי או מעלה"],
            index=self.ui.get_selectbox_index(["בחר תשובה", "תיכון", "הכשרה מקצועית", "תואר ראשון",
                     "תואר שני", "תואר שלישי או מעלה"],
                                              existing_profile.education if existing_profile else "בחר תשובה")
        )

        # Section 2: Social and Cultural Background (neutral framing)
        st.markdown("### 🏛️ רקע חברתי ותרבותי")
        st.caption("שאלות על השתייכות חברתית ותרבותית")

        religiosity = st.select_slider(
            "איך היית מגדיר את עצמך בהקשר הדתי?",
            options=["חילוני", "מסורתי", "דתי", "חרדי"],
            value=["חילוני", "מסורתי", "דתי", "חרדי"][
                existing_profile.religiosity - 1 if existing_profile and existing_profile.religiosity > 0 else 0]
        )

        # Convert back to numeric scale
        religiosity_map = {"חילוני": 1, "מסורתי": 2, "דתי": 3, "חרדי": 4}
        religiosity_numeric = religiosity_map.get(religiosity, 1)

        # Section 3: Political and Social Views (presented neutrally)
        st.markdown("### 🗳️ השקפות חברתיות")
        st.caption("שאלות על השקפות וגישות חברתיות כלליות")

        political_stance = st.select_slider(
            "באיזה חלק של הקשת החברתית-פוליטית היית ממקם את עצמך?",
            options=["שמאל", "מרכז-שמאל", "מרכז", "מרכז-ימין", "ימין"],
            value=["שמאל", "מרכז-שמאל", "מרכז", "מרכז-ימין", "ימין"][
                existing_profile.political_stance - 1 if existing_profile and existing_profile.political_stance > 0 else 2]
        )

        # Convert to numeric
        political_map = {"שמאל": 1, "מרכז-שמאל": 2, "מרכז": 3, "מרכז-ימין": 4, "ימין": 5}
        political_numeric = political_map.get(political_stance, 3)

        # Section 4: Civic Engagement (neutral presentation)
        st.markdown("### 🏛️ מעורבות אזרחית")
        st.caption("שאלות על מעורבות בחיים הציבוריים")

        col1, col2 = st.columns(2)

        with col1:
            voting_frequency = st.selectbox(
                "האם אתה נוהג להצביע בבחירות?",
                options=["בחר תשובה", "כן, תמיד", "ברוב המקרים", "לעיתים", "כמעט אף פעם", "אף פעם"],
                index=self.ui.get_selectbox_index(
                    ["בחר תשובה", "כן, תמיד", "ברוב המקרים", "לעיתים", "כמעט אף פעם", "אף פעם"],
                    existing_profile.voting_frequency if existing_profile else "בחר תשובה")
            )

            protest_participation = st.selectbox(
                "השתתפות בהפגנות או עצרות (בשנתיים האחרונות):",
                options=["בחר תשובה", "לא השתתפתי", "השתתפתי באירוע אחד",
                         "השתתפתי במספר אירועים", "השתתפתי באירועים רבים"],
                index=self.ui.get_selectbox_index(["בחר תשובה", "לא השתתפתי", "השתתפתי באירוע אחד",
                                                   "השתתפתי במספר אירועים", "השתתפתי באירועים רבים"],
                                                  existing_profile.protest_participation if existing_profile else "בחר תשובה")
            )

        with col2:
            political_discussions = st.selectbox(
                "עד כמה אתה נוהג לדון בנושאים חברתיים עם אחרים?",
                options=["בחר תשובה", "כמעט אף פעם", "לעיתים רחוקות", "לעיתים", "לעיתים קרובות", "בקביעות"],
                index=self.ui.get_selectbox_index(
                    ["בחר תשובה", "כמעט אף פעם", "לעיתים רחוקות", "לעיתים", "לעיתים קרובות", "בקביעות"],
                    existing_profile.political_discussions if existing_profile else "בחר תשובה")
            )

            social_media_activity = st.selectbox(
                "עד כמה אתה פעיל ברשתות חברתיות בנושאים חברתיים?",
                options=["בחר תשובה", "כלל לא פעיל", "קורא אבל לא מגיב",
                         "מגיב לעיתים", "משתף ומגיב", "פעיל מאוד"],
                index=self.ui.get_selectbox_index(["בחר תשובה", "כלל לא פעיל", "קורא אבל לא מגיב",
                                                   "מגיב לעיתים", "משתף ומגיב", "פעיל מאוד"],
                                                  existing_profile.social_media_activity if existing_profile else "בחר תשובה")
            )

        # Section 5: Information Sources (neutral)
        influence_sources = st.multiselect(
            "מאיזה מקורות אתה בדרך כלל מקבל מידע על נושאים חברתיים? (ניתן לבחור מספר אפשרויות)",
            options=["חברים ומשפחה", "עיתונות מקצועית", "רשתות חברתיות",
                     "אתרי חדשות", "רדיו וטלוויזיה", "מנהיגי דעת קהל",
                     "ספרים ומחקרים אקדמיים", "ניסיון אישי"],
            default=existing_profile.influence_sources if existing_profile else [],
            placeholder="בחר מקורות מידע"
        )

        # Section 6: Attitude Scales (neutral presentation)
        st.markdown("### 📊 עמדות כלליות")
        st.caption("דרג את עמדתך בנושאים הבאים (אין תשובות נכונות או שגויות)")

        col1, col2 = st.columns(2)

        with col1:
            trust_political_system = st.slider(
                "רמת האמון במוסדות הציבוריים בישראל:",
                min_value=1, max_value=10,
                value=existing_profile.trust_political_system if existing_profile else 5
            )
            st.caption("1 = אין אמון כלל | 5 = אמון בינוני | 10 = אמון מלא")

            political_efficacy = st.slider(
                "עד כמה אתה מרגיש שיש לך השפעה על מה שקורה במדינה:",
                min_value=1, max_value=10,
                value=existing_profile.political_efficacy if existing_profile else 5
            )
            st.caption("1 = אין השפעה כלל | 5 = השפעה בינונית | 10 = השפעה רבה מאוד")

        with col2:
            political_anxiety = st.slider(
                "רמת החששה מהמצב הכללי במדינה:",
                min_value=1, max_value=10,
                value=existing_profile.political_anxiety if existing_profile else 5
            )
            st.caption("1 = לא מודאג כלל | 5 = דאגה בינונית | 10 = מודאג מאוד")

        # Section 7: Party Feeling Thermometer (randomized order, neutral presentation)
        feeling_thermometer = self._render_feeling_thermometer(existing_profile, is_pre=True)

        # Section 8: Social Distance (neutral framing)
        social_distance = self._render_social_distance(existing_profile, is_pre=True)

        return {
            "gender": gender if gender != "בחר תשובה" else "",
            "age": age,
            "marital_status": marital_status if marital_status != "בחר תשובה" else "",
            "region": region if region != "בחר תשובה" else "",
            "religiosity": religiosity_numeric,
            "education": education if education != "בחר תשובה" else "",
            "political_stance": political_numeric,
            "protest_participation": protest_participation if protest_participation != "בחר תשובה" else "",
            "influence_sources": influence_sources,
            "voting_frequency": voting_frequency if voting_frequency != "בחר תשובה" else "",
            "political_discussions": political_discussions if political_discussions != "בחר תשובה" else "",
            "social_media_activity": social_media_activity if social_media_activity != "בחר תשובה" else "",
            "trust_political_system": trust_political_system,
            "political_efficacy": political_efficacy,
            "political_anxiety": political_anxiety,
            "feeling_thermometer_pre": feeling_thermometer,
            "social_distance_pre": social_distance
        }

    def _render_feeling_thermometer(self, existing_profile: Optional[UserProfile], is_pre: bool = True) -> Dict[
        str, int]:
        """Render feeling thermometer with randomized party order to avoid bias."""
        st.markdown("### 🌡️ דירוג רגשי למפלגות")
        st.caption("""
        דרג את הרגש שלך כלפי המפלגות הבאות, כאשר:
        * 0 = רגש שלילי מאוד
        * 50 = ניטרלי/אין דעה מיוחדת  
        * 100 = רגש חיובי מאוד
        """)

        parties = ["הליכוד", "יש עתיד", "הציונות הדתית", "המחנה הממלכתי",
                   "ש״ס", "יהדות התורה", "ישראל ביתנו",
                   "חד״ש - תע״ל", "רע״מ", "העבודה", "עוצמה יהודית", "נעם"]

        # Randomize party order to avoid order bias
        randomized_parties = parties.copy()
        random.shuffle(randomized_parties)

        feeling_thermometer = {}

        # Use existing data for comparison
        existing_data = {}
        if existing_profile:
            existing_data = existing_profile.feeling_thermometer_pre if is_pre else existing_profile.feeling_thermometer_post

        col1, col2 = st.columns(2)
        for i, party in enumerate(randomized_parties):
            with col1 if i % 2 == 0 else col2:
                feeling_thermometer[party] = st.slider(
                    f"{party}:",
                    min_value=0, max_value=100,
                    value=existing_data.get(party, 50),
                    key=f"feeling_{party}_{('pre' if is_pre else 'post')}"
                )

        return feeling_thermometer

    def _render_social_distance(self, existing_profile: Optional[UserProfile], is_pre: bool = True) -> Dict[str, int]:
        """Render social distance questions with neutral framing."""
        st.markdown("### 🤝 מרחק חברתי")
        st.caption("""
        עד כמה היית מרגיש בנוח במצבים הבאים עם אנשים שיש להם השקפות חברתיות-פוליטיות שונות מאוד משלך?

        * 1 = מאוד לא בנוח
        * 6 = מאוד בנוח
        """)

        social_situations = [
            "לגור באותה השכונה",
            "לעבוד במקום עבודה משותף",
            "לפתח חברות אישית",
            "שבן/בת משפחה יהיה בקשר זוגי עם אדם כזה"
        ]

        social_distance = {}

        # Use existing data for comparison
        existing_data = {}
        if existing_profile:
            existing_data = existing_profile.social_distance_pre if is_pre else existing_profile.social_distance_post

        for situation in social_situations:
            social_distance[situation] = st.slider(
                f"{situation}:",
                min_value=1, max_value=6,
                value=existing_data.get(situation, 3),
                key=f"social_{situation}_{('pre' if is_pre else 'post')}"
            )

        return social_distance

    def _render_post_chat_form(self, existing_profile: UserProfile) -> Dict[str, Any]:
        """Render post-chat questionnaire to measure changes."""
        st.markdown("### 🔄 לאחר השיחה")
        st.caption("כעת נבקש לענות שוב על כמה שאלות דומות, כדי לבחון האם השיחה השפיעה על דעותיך")

        # Key attitude measures (same as pre-chat)
        col1, col2 = st.columns(2)

        with col1:
            trust_political_system_post = st.slider(
                "רמת האמון במוסדות הציבוריים כעת:",
                min_value=1, max_value=10,
                value=existing_profile.trust_political_system,
                key="trust_post"
            )
            st.caption("1 = אין אמון כלל | 5 = אמון בינוני | 10 = אמון מלא")

        with col2:
            political_efficacy_post = st.slider(
                "עד כמה אתה מרגיש כעת שיש לך השפעה על מה שקורה במדינה:",
                min_value=1, max_value=10,
                value=existing_profile.political_efficacy,
                key="efficacy_post"
            )
            st.caption("1 = אין השפעה כלל | 5 = השפעה בינונית | 10 = השפעה רבה מאוד")

        # Post-chat feeling thermometer and social distance
        feeling_thermometer_post = self._render_feeling_thermometer(existing_profile, is_pre=False)
        social_distance_post = self._render_social_distance(existing_profile, is_pre=False)

        # Additional reflection questions
        st.markdown("### 💭 רפלקציה על השיחה")

        conversation_impact = st.selectbox(
            "האם השיחה השפיעה על דעותיך או נקודות המבט שלך?",
            options=["לא השפיעה כלל", "השפיעה מעט", "השפיעה במידה בינונית",
                     "השפיעה הרבה", "השפיעה מאוד"],
            key="conversation_impact"
        )

        most_interesting = st.text_area(
            "מה היה הדבר הכי מעניין או מפתיע בשיחה? (אופציונלי)",
            placeholder="תוכל לכתוב כאן מה עלה בשיחה שהיה מעניין או חדש בעיניך...",
            key="most_interesting"
        )

        changed_mind = st.text_area(
            "האם יש נושא שהשיחה גרמה לך לחשוב עליו אחרת? (אופציונלי)",
            placeholder="אם כן, תוכל לתאר בקצרה באיזה נושא ואיך השתנתה דעתך...",
            key="changed_mind"
        )

        return {
            "trust_political_system_post": trust_political_system_post,
            "political_efficacy_post": political_efficacy_post,
            "feeling_thermometer_post": feeling_thermometer_post,
            "social_distance_post": social_distance_post,
            "conversation_impact": conversation_impact,
            "most_interesting": most_interesting,
            "changed_mind": changed_mind
        }

    def _update_profile_with_post_data(self, profile: UserProfile, post_data: Dict[str, Any]) -> None:
        """Update profile with post-chat data."""
        profile.trust_political_system_post = post_data["trust_political_system_post"]
        profile.political_efficacy_post = post_data["political_efficacy_post"]
        profile.feeling_thermometer_post = post_data["feeling_thermometer_post"]
        profile.social_distance_post = post_data["social_distance_post"]

    def _calculate_attitude_changes(self, profile: UserProfile) -> None:
        """Calculate and summarize attitude changes."""
        changes = []

        # Trust change
        trust_change = abs(profile.trust_political_system - profile.trust_political_system_post)
        if trust_change >= 2:
            direction = "עלה" if profile.trust_political_system_post > profile.trust_political_system else "ירד"
            changes.append(f"אמון במערכת: {direction} ב-{trust_change} נקודות")

        # Efficacy change
        efficacy_change = abs(profile.political_efficacy - profile.political_efficacy_post)
        if efficacy_change >= 2:
            direction = "עלתה" if profile.political_efficacy_post > profile.political_efficacy else "ירדה"
            changes.append(f"תחושת השפעה: {direction} ב-{efficacy_change} נקודות")

        # Feeling thermometer changes (significant = 15+ points change)
        thermometer_changes = 0
        for party in profile.feeling_thermometer_pre:
            if party in profile.feeling_thermometer_post:
                change = abs(profile.feeling_thermometer_pre[party] - profile.feeling_thermometer_post[party])
                if change >= 15:
                    thermometer_changes += 1

        if thermometer_changes > 0:
            changes.append(f"דירוג רגשי למפלגות: שינוי משמעותי ב-{thermometer_changes} מפלגות")

        profile.attitude_change_detected = len(changes) > 0
        profile.change_summary = "; ".join(changes) if changes else "לא זוהו שינויים משמעותיים"

    def _render_participation_summary(self) -> None:
        """Render participation summary."""
        profile = st.session_state.get("temp_user_profile")
        messages = st.session_state.get("messages", [])

        if not profile:
            return

        st.markdown("### 📈 סיכום ההשתתפות")

        # Basic stats
        message_count = len(messages)
        user_messages = len([m for m in messages if m["role"] == "user"])
        duration = self._calculate_duration(messages)

        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("משך השיחה", f"{duration:.1f} דקות")
        with col2:
            st.metric("הודעות שכתבת", user_messages)
        with col3:
            st.metric("סך הודעות", message_count)

        # Attitude changes summary
        if hasattr(profile, 'attitude_change_detected'):
            st.markdown("### 🔄 זיהוי שינויים")
            if profile.attitude_change_detected:
                st.info(f"זוהו השינויים הבאים: {profile.change_summary}")
            else:
                st.success("לא זוהו שינויים משמעותיים בעמדות לאחר השיחה")

    def _validate_questionnaire(self, profile_data: Dict[str, Any], skip_validation: bool) -> bool:
        """Validate questionnaire data."""
        if skip_validation:
            return True

        # Check all required fields (excluding those that can be empty arrays or have defaults)
        required_fields = {
            "gender": "מגדר",
            "age": "גיל",
            "marital_status": "מצב משפחתי",
            "region": "אזור מגורים",
            "education": "השכלה",
            "voting_frequency": "תדירות הצבעה",
            "protest_participation": "השתתפות בהפגנות",
            "political_discussions": "דיונים פוליטיים",
            "social_media_activity": "פעילות ברשתות חברתיות"
        }

        missing_fields = []

        for field_key, field_name in required_fields.items():
            value = profile_data.get(field_key)
            # Check if field is empty, None, or "בחר תשובה"
            if not value or value == "" or value == "בחר תשובה":
                missing_fields.append(field_name)

        # Check age separately (must be > 0)
        if profile_data.get("age", 0) <= 0:
            missing_fields.append("גיל")

        # Check influence_sources (must have at least one selection)
        if not profile_data.get("influence_sources") or len(profile_data.get("influence_sources", [])) == 0:
            missing_fields.append("מקורות מידע")

        if missing_fields:
            st.error(f"אנא השלם את השדות הבאים: {', '.join(missing_fields)}")
            st.error("או סמן 'דלג על שדות שלא מולאו' כדי להמשיך")
            return False

        return True

    def _create_user_profile(self, profile_data: Dict[str, Any],
                             existing_profile: Optional[UserProfile]) -> UserProfile:
        """Create or update user profile."""
        if existing_profile:
            # Update existing profile
            for key, value in profile_data.items():
                setattr(existing_profile, key, value)
            return existing_profile
        else:
            # Create new profile
            return UserProfile(**profile_data)

    def _save_temp_user_profile(self, profile: UserProfile) -> None:
        """Save user profile to temporary session state."""
        st.session_state.temp_user_profile = profile
        st.session_state.questionnaire_completed = True

    def _render_sidebar(self) -> None:
        """Render responsive sidebar controls."""
        with st.sidebar:
            st.header("⚙️ אפשרויות")

            st.markdown("")

            if st.button("חזרה לשאלון", use_container_width=True):
                st.session_state.questionnaire_completed = False
                st.rerun()

            st.markdown("---")

            if st.button("סיים שיחה", use_container_width=True, type="primary"):
                st.session_state.conversation_finished = True
                st.rerun()

            st.markdown("---")
            st.caption("💡 תוכל לסיים את השיחה בכל שלב ולעבור לשאלון הסיכום")

    def _render_chat_history(self) -> None:
        """Render chat history."""
        messages = st.session_state.get("messages", [])
        for message in messages:
            with st.chat_message(message["role"]):
                self.ui.render_rtl_message(message["content"])

    def _handle_user_input(self, prompt: str) -> None:
        """Handle user input with streaming response."""
        import time
        import random

        # Add user message
        self._add_message("user", prompt)
        with st.chat_message("user"):
            self.ui.render_rtl_message(prompt)

        # Generate response
        with st.chat_message("assistant"):
            response_placeholder = st.empty()
            user_profile = st.session_state.get("temp_user_profile")

            # Minimal thinking message
            thinking_options = ["🤔 חושב...", "🔍 מחפש מידע...", "💭 מנתח..."]
            thinking_msg = random.choice(thinking_options)

            response_placeholder.markdown(
                f'<div class="streaming-text">{thinking_msg}</div>',
                unsafe_allow_html=True
            )

            # Get the real response
            full_response = ""
            try:
                chat_context = self._get_chat_context()
                first_chunk = True

                for chunk in self.ai_service.generate_response_stream(prompt, user_profile, chat_context):
                    if chunk and chunk.strip():
                        if first_chunk:
                            full_response = chunk
                            first_chunk = False
                        else:
                            full_response += chunk

                        response_placeholder.markdown(
                            f'<div class="streaming-text">{full_response}</div>',
                            unsafe_allow_html=True
                        )

                if full_response:
                    self._add_message("assistant", full_response)

            except Exception as e:
                error_msg = f"❌ שגיאה: {str(e)}"
                response_placeholder.markdown(
                    f'<div class="streaming-text">{error_msg}</div>',
                    unsafe_allow_html=True
                )
                self._add_message("assistant", error_msg)

    # ... (include all other existing methods like _verify_admin_password, render_admin_dashboard, etc.)

    def _verify_admin_password(self, password: str) -> bool:
        """Verify admin password."""
        try:
            admin_password = st.secrets["ADMIN_PASSWORD"]
            return password == admin_password
        except KeyError:
            st.error("❌ סיסמת מנהל לא מוגדרת במערכת")
            return False
        except Exception as e:
            st.error(f"❌ שגיאה בקריאת סיסמת המנהל: {str(e)}")
            return False

    def render_admin_dashboard(self) -> None:
        """Render admin dashboard with enhanced data viewer."""
        self.ui.render_header("📊 צפייה בנתוני המחקר",
                              "דף ניהול נתונים עבור החוקרים",
                              "כאן תוכל לראות, לנתח ולייצא את נתוני המחקר")

        # Enhanced data viewer with export
        exporter = DataExporter(self.data_service)
        exporter.render_data_viewer_section()

        # Navigation
        st.markdown("---")
        col1, col2 = st.columns(2)
        with col1:
            if st.button("🔙 חזרה לתפריט הראשי", use_container_width=True):
                st.session_state.app_mode = "main_menu"
                st.session_state.admin_authenticated = False
                st.rerun()
        with col2:
            if st.button("🔄 רענן נתונים", use_container_width=True):
                st.rerun()

    def _render_final_navigation(self) -> None:
        """Render final page navigation."""
        st.markdown("### 🔄 אפשרויות נוספות")
        col1, col2, col3 = st.columns(3)

        with col1:
            if st.button("🔁 השתתפות נוספת", use_container_width=True):
                self._reset_application()

        with col2:
            if st.button("🏠 דף הבית", use_container_width=True):
                self._reset_to_main_menu()

        with col3:
            st.markdown("📧 שאלות: research@university.ac.il")

    def _save_conversation_data(self) -> bool:
        """Save conversation data."""
        try:
            profile = st.session_state.get("temp_user_profile")
            messages = st.session_state.get("messages", [])

            if not profile or len(messages) == 0:
                st.error("שגיאה: לא נמצא פרופיל משתמש או שיחה ריקה")
                return False

            session_data = {
                "session_id": profile.session_id,
                "created_at": profile.created_at,
                "finished_at": datetime.now().isoformat(),
                "user_profile": asdict(profile),
                "conversation": messages,
                "conversation_stats": {
                    "total_messages": len(messages),
                    "user_messages": len([m for m in messages if m["role"] == "user"]),
                    "bot_messages": len([m for m in messages if m["role"] == "assistant"]),
                    "duration_minutes": self._calculate_duration(messages)
                }
            }

            return self.data_service.save_conversation(session_data)

        except Exception as e:
            st.error(f"שגיאה בשמירת השיחה: {str(e)}")
            return False

    def _calculate_duration(self, messages: List[Dict]) -> float:
        """Calculate conversation duration in minutes."""
        if not messages or len(messages) < 2:
            return 0.0
        try:
            start_time = datetime.fromisoformat(messages[0]["timestamp"])
            end_time = datetime.fromisoformat(messages[-1]["timestamp"])
            return round((end_time - start_time).total_seconds() / 60, 2)
        except:
            return 0.0

    def _add_message(self, role: str, content: str) -> None:
        """Add message to chat history."""
        message = ChatMessage(role=role, content=content)
        if "messages" not in st.session_state:
            st.session_state.messages = []
        st.session_state.messages.append(message.to_dict())

    def _get_chat_context(self) -> str:
        """Get formatted chat context."""
        messages = st.session_state.get("messages", [])
        if not messages:
            return ""

        context_parts = []
        for msg in messages:
            role_label = "משתמש" if msg["role"] == "user" else "עוזר"
            context_parts.append(f"{role_label}: {msg['content']}")

        return "\n\n".join(context_parts)

    def _clear_chat_history(self) -> None:
        """Clear chat history."""
        st.session_state.messages = []

    def _reset_to_questionnaire(self) -> None:
        """Reset to questionnaire."""
        st.session_state.questionnaire_completed = False
        st.session_state.conversation_finished = False
        self._clear_chat_history()
        st.rerun()

    def _reset_to_main_menu(self) -> None:
        """Reset to main menu."""
        st.session_state.app_mode = "main_menu"
        st.session_state.questionnaire_completed = False
        st.session_state.conversation_finished = False
        st.session_state.post_questionnaire_completed = False
        self._clear_chat_history()
        st.rerun()

    def _reset_application(self) -> None:
        """Reset entire application for new participation."""
        for key in list(st.session_state.keys()):
            del st.session_state[key]
        st.rerun()