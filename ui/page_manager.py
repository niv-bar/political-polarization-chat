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
    """Manages all page rendering for the research application."""

    def __init__(self, data_service: DataService, ai_service: Optional[AIService] = None):
        self.data_service = data_service
        self.ai_service = ai_service
        self.ui = UIComponents()

    def render_main_menu(self) -> None:
        """Render main menu with user and admin options."""
        st.markdown("# 🔬 מחקר אקדמי על דעות ועמדות בחברה הישראלית")

        st.markdown("""
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
""", unsafe_allow_html=False)

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
        """Render pre-chat questionnaire."""
        self.ui.render_header(
            "📋 שאלון רקע דמוגרפי וחברתי",
            "שלב ראשון: מידע כללי",
            "כדי להבין טוב יותר את הרקע החברתי של המשתתפים במחקר, נבקש לענות על כמה שאלות בסיסיות."
        )

        existing_profile = st.session_state.get("temp_user_profile")

        with st.form("user_questionnaire"):
            profile_data = self._render_questionnaire_form(existing_profile)
            skip_validation = st.checkbox(
                "דלג על שדות שלא מולאו",
                help="באפשרותך להמשיך גם מבלי למלא את כל השדות"
            )
            submitted = st.form_submit_button("← המשך לשיחה", use_container_width=True, type="primary")

            if submitted:
                if self._validate_questionnaire(profile_data, skip_validation):
                    user_profile = self._create_user_profile(profile_data, existing_profile)
                    self._save_temp_user_profile(user_profile)
                    st.success("תודה על מילוי השאלון! עובר לשיחה...")
                    st.rerun()
                    return True

        if st.button("→ חזרה לדף הבית", use_container_width=True):
            st.session_state.app_mode = "main_menu"
            st.rerun()

        return False

    def render_chat_interface(self) -> None:
        """Render chat interface."""
        self.ui.render_header(
            "💬 שיחה חופשית",
            "שלב שני: דיאלוג פתוח",
            "כעת תוכלו לנהל שיחה חופשית על נושאים שונים. השיחה תימשך כ-10-15 דקות."
        )
        self._render_sidebar()

        if not self.ai_service:
            st.error("❌ שירות הבינה המלאכותית אינו זמין כעת")
            return

        # Initial message
        if not st.session_state.get("messages"):
            with st.chat_message("assistant"):
                self.ui.render_rtl_message(
                    """שלום! אני כאן כדי לנהל איתך שיחה על נושאים שונים בחברה הישראלית. 
תוכל לשאול אותי על כל נושא שמעניין אותך - פוליטיקה, חברה, כלכלה, או כל דבר אחר. 
המטרה היא לנהל שיחה פתוחה וכנה.

על מה תרצה לדבר?"""
                )

        self._render_chat_history()

        if prompt := st.chat_input("כתוב הודעה..."):
            self._handle_user_input(prompt)

    def render_post_chat_questionnaire(self) -> None:
        """Render post-chat questionnaire."""
        self.ui.render_header(
            "📊 שאלון סיכום",
            "שלב שלישי: שאלון סיום",
            "לאחר השיחה, נבקש לענות על כמה שאלות קצרות נוספות."
        )

        existing_profile = st.session_state.get("temp_user_profile")
        if not existing_profile:
            st.error("שגיאה: לא נמצא מידע על המשתתף")
            return

        self._ensure_profile_compatibility(existing_profile)
        post_data = self._render_post_chat_form(existing_profile)
        self._update_profile_with_post_data(existing_profile, post_data)
        st.session_state.temp_user_profile = existing_profile

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

    def render_admin_dashboard(self) -> None:
        """Render admin dashboard."""
        self.ui.render_header(
            "📊 צפייה בנתוני המחקר",
            "דף ניהול נתונים עבור החוקרים",
            "כאן תוכל לראות, לנתח ולייצא את נתוני המחקר"
        )

        exporter = DataExporter(self.data_service)
        exporter.render_data_viewer_section()

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

    # Form rendering methods
    def _render_questionnaire_form(self, existing_profile: Optional[UserProfile]) -> Dict[str, Any]:
        """Render questionnaire form fields."""
        if existing_profile:
            self._ensure_profile_compatibility(existing_profile)

        # Demographics
        st.markdown("### 👤 מידע בסיסי")
        st.caption("מידע דמוגרפי בסיסי לצורך ניתוח המחקר")

        col1, col2 = st.columns(2)
        with col1:
            age = st.number_input(
                "גיל:", min_value=18, max_value=120,
                value=existing_profile.age if existing_profile and existing_profile.age > 0 else 30
            )
            gender = self._render_select(
                "מגדר:",
                ["בחר/י תשובה", "זכר", "נקבה", "אחר"],
                existing_profile.gender if existing_profile else None
            )

        with col2:
            region = self._render_select(
                "אזור מגורים:",
                ["בחר/י תשובה", "חיפה והצפון", "אזור השרון", "אזור הדרום",
                 "אזור ירושלים", "תל-אביב והמרכז", "יהודה ושומרון"],
                existing_profile.region if existing_profile else None
            )
            marital_status = self._render_select(
                "מצב משפחתי:",
                ["בחר/י תשובה", "רווק/ה", "נשוי/נשואה", "בזוגיות", "גרוש/ה", "אלמן/ה"],
                existing_profile.marital_status if existing_profile else None
            )

        education = self._render_select(
            "השכלה:",
            ["בחר/י תשובה", "תיכון", "הכשרה מקצועית", "תואר ראשון", "תואר שני", "תואר שלישי או מעלה"],
            existing_profile.education if existing_profile else None
        )

        # Social background
        st.markdown("### 🏛️ רקע חברתי ותרבותי")
        st.caption("שאלות על השתייכות חברתית ותרבותית")

        religiosity = st.select_slider(
            "איך היית מגדיר/ה את עצמך בהקשר הדתי?",
            options=["חילוני", "מסורתי", "דתי", "חרדי"],
            value=self._get_religiosity_label(existing_profile.religiosity if existing_profile else 1)
        )
        religiosity_numeric = {"חילוני": 1, "מסורתי": 2, "דתי": 3, "חרדי": 4}[religiosity]

        # Political views
        st.markdown("### 🗳️ השקפות חברתיות")
        st.caption("שאלות על השקפות וגישות חברתיות כלליות")

        political_stance = st.select_slider(
            "באיזה חלק של הקשת החברתית-פוליטית את/ה?",
            options=["שמאל", "מרכז-שמאל", "מרכז", "מרכז-ימין", "ימין"],
            value=self._get_political_label(existing_profile.political_stance if existing_profile else 3)
        )
        political_numeric = {"שמאל": 1, "מרכז-שמאל": 2, "מרכז": 3, "מרכז-ימין": 4, "ימין": 5}[political_stance]

        # Voting behavior
        st.markdown("### 📊 התנהגות הצבעה ותפיסות פוליטיות")
        st.caption("שאלות על התנהגות הצבעה וגישות כלפי המערכת הפוליטית")

        last_election_vote = self._render_select(
            "למי הצבעת בבחירות הכנסת האחרונות?",
            ["בחר/י תשובה", "הליכוד", "יש עתיד", "הציונות הדתית", "המחנה הממלכתי",
             "שס", "יהדות התורה", "ישראל ביתנו", "חדש-תעל", "רעמ", "העבודה",
             "מרץ", "בלד", "עוצמה יהודית", "אחר", "לא הצבעתי"],
            getattr(existing_profile, 'last_election_vote', '') if existing_profile else None
        )

        polarization_perception = self._render_select(
            "האם לדעתך הקיטוב הפוליטי גבר בישראל בשלוש השנים האחרונות?",
            ["בחר/י תשובה", "הקיטוב גבר", "הקיטוב לא השתנה", "הקיטוב פחת"],
            getattr(existing_profile, 'polarization_perception', '') if existing_profile else None
        )

        # Civic engagement
        st.markdown("### 🏛️ מעורבות אזרחית")
        st.caption("שאלות על מעורבות בחיים הציבוריים")

        col1, col2, col3 = st.columns(3)
        with col1:
            voting_frequency = self._render_select(
                "האם את/ה נוהג להצביע בבחירות?",
                ["בחר/י תשובה", "כן, תמיד", "ברוב המקרים", "לעיתים", "כמעט אף פעם", "אף פעם"],
                existing_profile.voting_frequency if existing_profile else None
            )

        with col2:
            protest_participation = self._render_select(
                "השתתפות בהפגנות או עצרות (בשנתיים האחרונות):",
                ["בחר/י תשובה", "לא השתתפתי", "השתתפתי באירוע אחד",
                 "השתתפתי במספר אירועים", "השתתפתי באירועים רבים"],
                existing_profile.protest_participation if existing_profile else None
            )

        with col3:
            military_service_recent = self._render_select(
                "האם שירתת במילואים בשנתיים האחרונות?",
                ["בחר/י תשובה", "כן, שירות מלא", "כן, שירות חלקי", "לא", "לא רלוונטי"],
                getattr(existing_profile, 'military_service_recent', '') if existing_profile else None
            )

        col1, col2 = st.columns(2)
        with col1:
            political_discussions = self._render_select(
                "עד כמה את/ה נוהג/ת לדון בנושאים חברתיים עם אחרים?",
                ["בחר/י תשובה", "כמעט אף פעם", "לעיתים רחוקות", "לעיתים", "לעיתים קרובות", "בקביעות"],
                existing_profile.political_discussions if existing_profile else None
            )

        with col2:
            social_media_activity = self._render_select(
                "עד כמה את/ה פעיל/ה ברשתות חברתיות בנושאים חברתיים?",
                ["בחר/י תשובה", "כלל לא פעיל/ה", "קורא/ת אבל לא מגיב/ה",
                 "מגיב/ה לעיתים", "משתף/פת ומגיב/ה", "פעיל/ה מאוד"],
                existing_profile.social_media_activity if existing_profile else None
            )

        # Information sources
        influence_sources = st.multiselect(
            "מאיזה מקורות את/ה בדרך כלל מקבל מידע על נושאים חברתיים? (ניתן לבחור מספר אפשרויות)",
            options=["חברים ומשפחה", "עיתונות מקצועית", "רשתות חברתיות", "אתרי חדשות",
                     "רדיו וטלוויזיה", "מנהיגי דעת קהל", "ספרים ומחקרים אקדמיים", "ניסיון אישי"],
            default=existing_profile.influence_sources if existing_profile else [],
            placeholder="בחר/י מקורות מידע"
        )

        # Attitude scales
        st.markdown("### 📊 עמדות כלליות")
        st.caption("דרג/י את עמדתך בנושאים הבאים (אין תשובות נכונות או שגויות)")

        col1, col2 = st.columns(2)
        with col1:
            trust_political_system = self._render_slider(
                "רמת האמון במוסדות הציבוריים בישראל:",
                "1 = אין אמון כלל | 5 = אמון בינוני | 10 = אמון מלא",
                existing_profile.trust_political_system if existing_profile else 5
            )
            political_efficacy = self._render_slider(
                "עד כמה אתה מרגיש שיש לך השפעה על מה שקורה במדינה:",
                "1 = אין השפעה כלל | 5 = השפעה בינונית | 10 = השפעה רבה מאוד",
                existing_profile.political_efficacy if existing_profile else 5
            )

        with col2:
            political_anxiety = self._render_slider(
                "רמת החששה מהמצב הכללי במדינה:",
                "1 = לא מודאג/ת כלל | 5 = דאגה בינונית | 10 = מודאג/ת מאוד",
                existing_profile.political_anxiety if existing_profile else 5
            )

        # NEW Gaza war questions
        st.markdown("### ⚔️ עמדה לגבי המלחמה בעזה")
        st.caption("מה עמדתך לגבי המלחמה בעזה?")

        col1, col2 = st.columns(2)
        with col1:
            war_priority_pre = self._render_select(
                "מבין שתי מטרות המלחמה, מה לדעתך המטרה החשובה יותר?",
                ["בחר/י תשובה", "החזרת החטופים", "מיטוט חמאס", "לא יודע/ת"],
                getattr(existing_profile, 'war_priority_pre', '') if existing_profile else None
            )

        with col2:
            israel_action_pre = self._render_select(
                "מה לדעתך ישראל צריכה לעשות עכשיו?",
                ["בחר/י תשובה", "עסקה לשחרור חטופים", "מבצע צבאי לכיבוש עזה", "לא יודע/ת"],
                getattr(existing_profile, 'israel_action_pre', '') if existing_profile else None
            )

        # Complex questions
        feeling_thermometer = self._render_feeling_thermometer(existing_profile, is_pre=True)
        social_distance = self._render_social_distance(existing_profile, is_pre=True)

        return {
            "gender": gender if gender != "בחר/י תשובה" else "",
            "age": age,
            "marital_status": marital_status if marital_status != "בחר/י תשובה" else "",
            "region": region if region != "בחר/י תשובה" else "",
            "religiosity": religiosity_numeric,
            "education": education if education != "בחר/י תשובה" else "",
            "political_stance": political_numeric,
            "last_election_vote": last_election_vote if last_election_vote != "בחר/י תשובה" else "",
            "polarization_perception": polarization_perception if polarization_perception != "בחר/י תשובה" else "",
            "protest_participation": protest_participation if protest_participation != "בחר/י תשובה" else "",
            "military_service_recent": military_service_recent if military_service_recent != "בחר/י תשובה" else "",
            "influence_sources": influence_sources,
            "voting_frequency": voting_frequency if voting_frequency != "בחר/י תשובה" else "",
            "political_discussions": political_discussions if political_discussions != "בחר/י תשובה" else "",
            "social_media_activity": social_media_activity if social_media_activity != "בחר/י תשובה" else "",
            "trust_political_system": trust_political_system,
            "political_efficacy": political_efficacy,
            "political_anxiety": political_anxiety,
            "war_priority_pre": war_priority_pre if war_priority_pre != "בחר/י תשובה" else "",
            "israel_action_pre": israel_action_pre if israel_action_pre != "בחר/י תשובה" else "",
            "feeling_thermometer_pre": feeling_thermometer,
            "social_distance_pre": social_distance
        }

    def _render_post_chat_form(self, existing_profile: UserProfile) -> Dict[str, Any]:
        """Render post-chat questionnaire form."""
        st.markdown("### 🔄 לאחר השיחה")
        st.caption("כעת נבקש לענות שוב על כמה שאלות דומות, כדי לבחון האם השיחה השפיעה על דעותיך")

        col1, col2 = st.columns(2)
        with col1:
            trust_post = self._render_slider(
                "רמת האמון במוסדות הציבוריים כעת:",
                "1 = אין אמון כלל | 5 = אמון בינוני | 10 = אמון מלא",
                5, "post_chat_trust_political_system"
            )

        with col2:
            efficacy_post = self._render_slider(
                "עד כמה את/ה מרגיש כעת שיש לך השפעה על מה שקורה במדינה:",
                "1 = אין השפעה כלל | 5 = השפעה בינונית | 10 = השפעה רבה מאוד",
                5, "post_chat_political_efficacy"
            )

        # NEW Gaza war questions - POST
        st.markdown("### ⚔️ עמדה לגבי המלחמה בעזה - לאחר השיחה")
        col1, col2 = st.columns(2)
        with col1:
            war_priority_post = self._render_select(
                "מבין שתי מטרות המלחמה, מה לדעתך המטרה החשובה יותר?",
                ["בחר/י תשובה", "החזרת החטופים", "מיטוט חמאס", "לא יודע/ת"],
                getattr(existing_profile, 'war_priority_post', ''),
                "post_chat_war_priority"
            )

        with col2:
            israel_action_post = self._render_select(
                "מה לדעתך ישראל צריכה לעשות עכשיו?",
                ["בחר/י תשובה", "עסקה לשחרור חטופים", "מבצע צבאי לכיבוש עזה", "לא יודע/ת"],
                getattr(existing_profile, 'israel_action_post', ''),
                "post_chat_israel_action"
            )

        feeling_thermometer_post = self._render_feeling_thermometer(existing_profile, is_pre=False, is_post_chat=True)
        social_distance_post = self._render_social_distance(existing_profile, is_pre=False, is_post_chat=True)

        # Reflection
        st.markdown("### 💭 רפלקציה על השיחה")

        impact = self._render_select(
            "האם השיחה השפיעה על דעותיך או נקודות המבט שלך?",
            ["בחר/י תשובה", "לא השפיעה כלל", "השפיעה מעט", "השפיעה במידה בינונית",
             "השפיעה הרבה", "השפיעה מאוד"],
            getattr(existing_profile, 'conversation_impact', ''),
            "post_chat_conversation_impact"
        )

        interesting = st.text_area(
            "מה היה הדבר הכי מעניין או מפתיע בשיחה? (אופציונלי)",
            value=getattr(existing_profile, 'most_interesting', ''),
            key="post_chat_most_interesting"
        )

        changed = st.text_area(
            "האם יש נושא שהשיחה גרמה לך לחשוב עליו אחרת? (אופציונלי)",
            value=getattr(existing_profile, 'changed_mind', ''),
            key="post_chat_changed_mind"
        )

        return {
            "trust_political_system_post": trust_post,
            "political_efficacy_post": efficacy_post,
            "war_priority_post": war_priority_post if war_priority_post != "בחר/י תשובה" else "",
            "israel_action_post": israel_action_post if israel_action_post != "בחר/י תשובה" else "",
            "feeling_thermometer_post": feeling_thermometer_post,
            "social_distance_post": social_distance_post,
            "conversation_impact": impact if impact != "בחר/י תשובה" else "",
            "most_interesting": interesting,
            "changed_mind": changed
        }

    def _render_feeling_thermometer(self, existing_profile: Optional[UserProfile],
                                    is_pre: bool = True, is_post_chat: bool = False) -> Dict[str, int]:
        """Render feeling thermometer for political parties."""
        st.markdown("### 🌡️ דירוג רגשי למפלגות")
        st.caption("""
        דרג/י את הרגש שלך כלפי המפלגות הבאות, כאשר:
        * 0 = רגש שלילי מאוד
        * 50 = ניטרלי/אין דעה מיוחדת  
        * 100 = רגש חיובי מאוד
        """)

        # Updated parties list
        parties = [
            "הליכוד",
            "יש עתיד",
            "הציונות הדתית",
            "המחנה הממלכתי",
            "ישראל ביתנו",
            "העבודה",
            "מרץ",
            "עוצמה יהודית",
            "המפלגות החרדיות",
            "המפלגות הערביות"
        ]

        # Randomize for pre-chat, keep order for post-chat
        if is_pre and not is_post_chat:
            parties = parties.copy()
            random.shuffle(parties)

        feeling_thermometer = {}
        existing_data = {}

        if existing_profile and not is_post_chat:
            existing_data = existing_profile.feeling_thermometer_pre if is_pre else existing_profile.feeling_thermometer_post

        col1, col2 = st.columns(2)
        for i, party in enumerate(parties):
            with col1 if i % 2 == 0 else col2:
                # Use stable keys - no timestamps
                key_suffix = f"{'postchat_' if is_post_chat else ''}feeling_{party.replace(' ', '_').replace('״', '').replace('־', '_')}_{('pre' if is_pre else 'post')}"

                feeling_thermometer[party] = st.slider(
                    f"{party}:",
                    min_value=0, max_value=100,
                    value=existing_data.get(party, 50) if not is_post_chat else 50,
                    key=key_suffix
                )

        return feeling_thermometer

    def _render_social_distance(self, existing_profile: Optional[UserProfile],
                                is_pre: bool = True, is_post_chat: bool = False) -> Dict[str, int]:
        """Render social distance questions."""
        st.markdown("### 🤝 מרחק חברתי")
        st.caption("""
        עד כמה היית מרגיש/ה בנוח במצבים הבאים עם אנשים שיש להם השקפות חברתיות-פוליטיות שונות מאוד משלך?
        * 1 = מאוד לא בנוח
        * 6 = מאוד בנוח
        """)

        situations = [
            "לגור באותה השכונה",
            "לעבוד במקום עבודה משותף",
            "לפתח חברות אישית",
            "שבן/בת משפחה יהיה בקשר זוגי עם אדם כזה"
        ]

        social_distance = {}
        existing_data = {}

        if existing_profile and not is_post_chat:
            existing_data = existing_profile.social_distance_pre if is_pre else existing_profile.social_distance_post

        for i, situation in enumerate(situations):
            # Use stable keys - no timestamps
            clean_situation = situation.replace('/', '_').replace(' ', '_').replace('-', '_')
            key_suffix = f"{'postchat_' if is_post_chat else ''}social_{clean_situation}_{('pre' if is_pre else 'post')}"

            social_distance[situation] = st.slider(
                f"{situation}:",
                min_value=1, max_value=6,
                value=existing_data.get(situation, 3) if not is_post_chat else 3,
                key=key_suffix
            )

        return social_distance

    # Helper methods
    def _render_select(self, label: str, options: List[str], current_value: Optional[str],
                       key: Optional[str] = None) -> str:
        """Helper to render select box with default handling."""
        current = current_value or "בחר/י תשובה"
        index = options.index(current) if current in options else 0
        return st.selectbox(label, options=options, index=index, key=key)

    def _render_slider(self, label: str, caption: str, default: int, key: Optional[str] = None) -> int:
        """Helper to render slider with caption."""
        value = st.slider(label, min_value=1, max_value=10, value=default, key=key)
        st.caption(caption)
        return value

    def _get_religiosity_label(self, value: int) -> str:
        """Convert religiosity number to label."""
        return ["חילוני", "מסורתי", "דתי", "חרדי"][max(0, min(3, value - 1))]

    def _get_political_label(self, value: int) -> str:
        """Convert political stance number to label."""
        return ["שמאל", "מרכז-שמאל", "מרכז", "מרכז-ימין", "ימין"][max(0, min(4, value - 1))]

    def _ensure_profile_compatibility(self, profile: UserProfile) -> None:
        """Ensure profile has all required fields."""
        defaults = {
            'last_election_vote': '',
            'polarization_perception': '',
            'military_service_recent': '',
            'war_priority_pre': '',  # UPDATED
            'israel_action_pre': '',  # UPDATED
            'war_priority_post': '',  # UPDATED
            'israel_action_post': '',  # UPDATED
            'conversation_impact': '',
            'most_interesting': '',
            'changed_mind': ''
        }

        for field, default in defaults.items():
            if not hasattr(profile, field):
                setattr(profile, field, default)

    def _validate_questionnaire(self, data: Dict[str, Any], skip: bool) -> bool:
        """Validate questionnaire completeness."""
        if skip:
            return True

        required = {
            "gender": "מגדר", "age": "גיל", "marital_status": "מצב משפחתי",
            "region": "אזור מגורים", "education": "השכלה",
            "last_election_vote": "הצבעה בבחירות האחרונות",
            "polarization_perception": "תפיסת הקיטוב הפוליטי",
            "voting_frequency": "תדירות הצבעה",
            "protest_participation": "השתתפות בהפגנות",
            "political_discussions": "דיונים פוליטיים",
            "social_media_activity": "פעילות ברשתות חברתיות"
        }

        missing = [name for key, name in required.items()
                   if not data.get(key) or data.get(key) == "בחר/י תשובה"]

        if data.get("age", 0) <= 0:
            missing.append("גיל")

        if not data.get("influence_sources"):
            missing.append("מקורות מידע")

        if missing:
            st.error(f"אנא השלם: {', '.join(missing)}")
            st.error("או סמן 'דלג על שדות שלא מולאו'")
            return False

        return True

    def _create_user_profile(self, data: Dict[str, Any],
                             existing: Optional[UserProfile]) -> UserProfile:
        """Create or update user profile."""
        if existing:
            self._ensure_profile_compatibility(existing)
            for key, value in data.items():
                setattr(existing, key, value)
            return existing

        profile = UserProfile(**data)
        self._ensure_profile_compatibility(profile)
        return profile

    def _save_temp_user_profile(self, profile: UserProfile) -> None:
        """Save profile to session."""
        st.session_state.temp_user_profile = profile
        st.session_state.questionnaire_completed = True

    def _update_profile_with_post_data(self, profile: UserProfile, data: Dict[str, Any]) -> None:
        """Update profile with post-chat data."""
        for key, value in data.items():
            setattr(profile, key, value)

    # Chat methods
    def _render_sidebar(self) -> None:
        """Render chat sidebar."""
        with st.sidebar:
            st.header("⚙️ אפשרויות")

            if st.button("חזרה לשאלון", use_container_width=True):
                st.session_state.questionnaire_completed = False
                st.rerun()

            st.markdown("---")

            if st.button("סיים שיחה", use_container_width=True, type="primary"):
                st.session_state.conversation_finished = True
                st.rerun()

            st.caption("💡 תוכל לסיים בכל שלב")

    def _render_chat_history(self) -> None:
        """Render chat message history."""
        for message in st.session_state.get("messages", []):
            with st.chat_message(message["role"]):
                self.ui.render_rtl_message(message["content"])

    def _handle_user_input(self, prompt: str) -> None:
        """Process user input and generate response."""
        import time

        # Add user message
        self._add_message("user", prompt)
        with st.chat_message("user"):
            self.ui.render_rtl_message(prompt)

        # Generate response
        with st.chat_message("assistant"):
            placeholder = st.empty()
            thinking = ["🤔 חושב...", "🔍 מחפש מידע...", "💭 מנתח..."][time.time_ns() % 3]
            placeholder.markdown(f'<div class="streaming-text">{thinking}</div>', unsafe_allow_html=True)

            try:
                profile = st.session_state.get("temp_user_profile")
                context = self._get_chat_context()
                full_response = ""

                for chunk in self.ai_service.generate_response_stream(prompt, profile, context):
                    if chunk and chunk.strip():
                        full_response += chunk
                        placeholder.markdown(
                            f'<div class="streaming-text">{full_response}</div>',
                            unsafe_allow_html=True
                        )

                if full_response:
                    self._add_message("assistant", full_response)

            except Exception as e:
                error = f"❌ שגיאה: {str(e)}"
                placeholder.markdown(f'<div class="streaming-text">{error}</div>', unsafe_allow_html=True)
                self._add_message("assistant", error)

    def _add_message(self, role: str, content: str) -> None:
        """Add message to history."""
        if "messages" not in st.session_state:
            st.session_state.messages = []

        message = ChatMessage(role=role, content=content)
        st.session_state.messages.append(message.to_dict())

    def _get_chat_context(self) -> str:
        """Get formatted chat context."""
        messages = st.session_state.get("messages", [])
        if not messages:
            return ""

        return "\n\n".join([
            f"{'משתמש' if msg['role'] == 'user' else 'עוזר'}: {msg['content']}"
            for msg in messages
        ])

    # Data methods
    def _save_conversation_data(self) -> bool:
        """Save conversation data."""
        try:
            profile = st.session_state.get("temp_user_profile")
            messages = st.session_state.get("messages", [])

            if not profile or not messages:
                st.error("שגיאה: חסרים נתונים")
                return False

            session_data = {
                "session_id": profile.session_id,
                "created_at": profile.created_at,
                "finished_at": datetime.now().isoformat(),
                "user_profile": asdict(profile),
                "conversation": messages,
                "session_info": {
                    "total_messages": len(messages),
                    "start_time": messages[0]["timestamp"] if messages else None,
                    "end_time": messages[-1]["timestamp"] if messages else None
                }
            }

            return self.data_service.save_conversation(session_data)

        except Exception as e:
            st.error(f"שגיאה בשמירה: {str(e)}")
            return False

    def _verify_admin_password(self, password: str) -> bool:
        """Verify admin password."""
        try:
            return password == st.secrets["ADMIN_PASSWORD"]
        except KeyError:
            st.error("❌ סיסמת מנהל לא מוגדרת")
            return False

    # Reset methods
    def _reset_application(self) -> None:
        """Reset application for new session."""
        for key in list(st.session_state.keys()):
            del st.session_state[key]
        st.rerun()

    def _reset_to_main_menu(self) -> None:
        """Reset to main menu."""
        keys_to_keep = []
        for key in list(st.session_state.keys()):
            if key not in keys_to_keep:
                del st.session_state[key]
        st.session_state.app_mode = "main_menu"
        st.rerun()