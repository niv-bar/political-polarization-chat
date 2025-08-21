import streamlit as st
from typing import Optional, List, Dict, Any
from datetime import datetime
from dataclasses import asdict
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
        self.ui.render_header("🗳️ מערכת מחקר קיטוב פוליטי",
                              "ברוכים הבאים למערכת המחקר",
                              "מערכת לחקר השפעת שיחות פוליטיות על דעות ועמדות")

        col1, col2, col3 = st.columns([1, 2, 1])

        with col2:
            st.markdown("### בחר את הנתיב המתאים:")

            # User path
            st.markdown("#### 👤 משתמש רגיל")
            st.markdown("השתתף במחקר על קיטוב פוליטי")
            if st.button("🚀 התחל סקר ושיחה", use_container_width=True, type="primary"):
                st.session_state.app_mode = "user"
                st.rerun()

            st.markdown("---")

            # Admin path
            st.markdown("#### 🔒 מנהל מחקר")
            st.markdown("גישה לנתוני המחקר (דורש סיסמה)")

            admin_password = st.text_input("הזן סיסמת מנהל:", type="password", placeholder="סיסמה...")

            if st.button("🔓 כניסה למערכת ניהול", use_container_width=True):
                if self._verify_admin_password(admin_password):
                    st.session_state.app_mode = "admin"
                    st.session_state.admin_authenticated = True
                    st.success("✅ כניסה מוצלחת למערכת ניהול")
                    st.rerun()
                else:
                    st.error("❌ סיסמה שגויה")

        self.ui.render_footer()

    def render_questionnaire(self) -> bool:
        """Render questionnaire and return True if completed."""
        self.ui.render_header("📋 שאלון מאפיינים אישיים ופוליטיים",
                              "אנא מלא/י את השאלון הבא לפני תחילת השיחה עם הבוט",
                              "המידע נשמר באופן זמני ורק לאחר סיום השיחה תוכל לבחור האם לשמור למחקר")

        existing_profile = st.session_state.get("temp_user_profile")

        with st.form("user_questionnaire"):
            profile_data = self._render_questionnaire_form(existing_profile)

            skip_validation = st.checkbox("דלג על שדות חובה ומעבר ישירות לצ'אט")
            submitted = st.form_submit_button("המשך לצ'אט 💬", use_container_width=True)

            if submitted:
                if self._validate_questionnaire(profile_data, skip_validation):
                    user_profile = self._create_user_profile(profile_data, existing_profile)
                    self._save_temp_user_profile(user_profile)
                    st.success(f"פרופיל נשמר זמנית! (מזהה: {user_profile.session_id[:8]}) מועבר לצ'אט...")
                    st.rerun()
                    return True

        # Navigation
        if st.button("🔙 חזרה לתפריט הראשי", use_container_width=True):
            st.session_state.app_mode = "main_menu"
            st.rerun()

        return False

    def render_chat_interface(self) -> None:
        """Render the main chat interface."""
        self.ui.render_header("🗳️ צ'אטבוט פוליטי")
        self._render_sidebar()

        if not self.ai_service:
            st.error("❌ שירות AI לא זמין")
            return

        # Render chat history
        self._render_chat_history()

        # Handle user input
        if prompt := st.chat_input("כתוב כאן..."):
            self._handle_user_input(prompt)

    def render_final_page(self) -> None:
        """Render final page after conversation completion."""
        self.ui.render_header("🎯 סיום השיחה",
                              "תודה על השתתפותך בשיחה עם הבוט הפוליטי!",
                              "להלן סיכום השיחה ואפשרות לשמור את הנתונים למחקר")

        # Show conversation summary
        self._render_conversation_summary()

        # Data saving option
        st.markdown("### 💾 שמירת נתונים למחקר")
        self.ui.render_rtl_message(
            "האם תרצה לשמור את נתוני השיחה למחקר על קיטוב פוליטי? הנתונים נשמרים באופן אנונימי במסד נתונים מאובטח.")

        col1, col2, col3 = st.columns([1, 1, 1])
        with col2:
            if st.button("💾 שמור נתונים למחקר", use_container_width=True, type="primary"):
                if self._save_conversation_data():
                    st.success("✅ הנתונים נשמרו בהצלחה במסד הנתונים! תודה על ההשתתפות במחקר.")
                    st.balloons()

        # Navigation options
        self._render_final_navigation()

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

    # Helper methods (private)
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

    def _render_questionnaire_form(self, existing_profile: Optional[UserProfile]) -> Dict[str, Any]:
        """Render questionnaire form fields and return form data."""
        st.markdown("### 📊 מידע דמוגרפי")

        gender = st.selectbox(
            "מגדר:",
            options=["", "זכר", "נקבה", "אחר", "מעדיף/ה לא לענות"],
            index=self.ui.get_selectbox_index(["", "זכר", "נקבה", "אחר", "מעדיף/ה לא לענות"],
                                              existing_profile.gender if existing_profile else "")
        )

        age = st.number_input("גיל:", min_value=18, max_value=120,
                              value=existing_profile.age if existing_profile and existing_profile.age > 0 else 25)

        marital_status = st.selectbox(
            "מצב משפחתי:",
            options=["", "רווק/ה", "נשוי/אה", "גרוש/ה", "אלמן/ה", "בזוגיות"],
            index=self.ui.get_selectbox_index(["", "רווק/ה", "נשוי/אה", "גרוש/ה", "אלמן/ה", "בזוגיות"],
                                              existing_profile.marital_status if existing_profile else "")
        )

        region = st.selectbox(
            "אזור מגורים:",
            options=["", "צפון", "מרכז", "ירושלים", "דרום", "יהודה ושומרון"],
            index=self.ui.get_selectbox_index(["", "צפון", "מרכז", "ירושלים", "דרום", "יהודה ושומרון"],
                                              existing_profile.region if existing_profile else "")
        )

        religiosity = st.slider("רמת דתיות (1=חילוני לגמרי, 10=דתי מאוד):", min_value=1, max_value=10,
                                value=existing_profile.religiosity if existing_profile else 5)

        st.markdown("### 🗳️ מידע פוליטי")

        political_stance = st.slider("עמדה פוליטית (1=שמאל קיצוני, 10=ימין קיצוני):", min_value=1, max_value=10,
                                     value=existing_profile.political_stance if existing_profile else 5)

        protest_participation = st.selectbox(
            "השתתפות בהפגנות בשנה האחרונה:",
            options=["", "לא השתתפתי", "השתתפתי מדי פעם", "השתתפתי רבות", "השתתפתי באופן קבוע"],
            index=self.ui.get_selectbox_index(
                ["", "לא השתתפתי", "השתתפתי מדי פעם", "השתתפתי רבות", "השתתפתי באופן קבוע"],
                existing_profile.protest_participation if existing_profile else "")
        )

        influence_sources = st.multiselect(
            "מקורות השפעה על דעותיך הפוליטיות:",
            options=["משפחה", "חברים", "מדיה מסורתית", "רשתות חברתיות", "פוליטיקאים", "אקדמיה",
                     "דת/מנהיגים רוחניים", "ניסיון אישי"],
            default=existing_profile.influence_sources if existing_profile else []
        )

        # Polarization measurements
        feeling_thermometer = self._render_feeling_thermometer(existing_profile)
        social_distance = self._render_social_distance(existing_profile)

        return {
            "gender": gender, "age": age, "marital_status": marital_status,
            "region": region, "religiosity": religiosity, "political_stance": political_stance,
            "protest_participation": protest_participation, "influence_sources": influence_sources,
            "feeling_thermometer": feeling_thermometer, "social_distance": social_distance
        }

    def _render_feeling_thermometer(self, existing_profile: Optional[UserProfile]) -> Dict[str, int]:
        """Render feeling thermometer section."""
        st.markdown("### 🌡️ מדדי קיטוב - מדי חום רגשי")
        st.caption("דרג/י את הרגש שלך כלפי מפלגות שונות (0=קר מאוד/שנאה חזקה, 100=חם מאוד/אהדה חזקה)")

        parties = ["ליכוד", "יש עתיד", "הציונות הדתית", "יהדות התורה", "העבודה", "מרץ", "ש״ס", "ישראל ביתנו"]
        feeling_thermometer = {}

        col1, col2 = st.columns(2)
        for i, party in enumerate(parties):
            with col1 if i % 2 == 0 else col2:
                feeling_thermometer[party] = st.slider(
                    f"{party}:",
                    min_value=0, max_value=100,
                    value=existing_profile.feeling_thermometer.get(party, 50) if existing_profile else 50
                )

        return feeling_thermometer

    def _render_social_distance(self, existing_profile: Optional[UserProfile]) -> Dict[str, int]:
        """Render social distance section."""
        st.markdown("### 🤝 מדד מרחק חברתי")
        st.caption("עד כמה היית מרגיש בנוח במצבים הבאים עם אנשים בעלי דעות פוליטיות שונות ממך?")
        st.caption("(1=מאוד לא נוח, 6=מאוד נוח)")

        social_situations = [
            "לחיות באותה השכונה",
            "לעבוד באותה מקום עבודה",
            "להיות חברים קרובים",
            "שבן/בת המשפחה שלי יתחתן עם מישהו מהקבוצה הזו"
        ]

        social_distance = {}
        for situation in social_situations:
            social_distance[situation] = st.slider(
                f"{situation}:",
                min_value=1, max_value=6,
                value=existing_profile.social_distance.get(situation, 3) if existing_profile else 3
            )

        return social_distance

    def _validate_questionnaire(self, profile_data: Dict[str, Any], skip_validation: bool) -> bool:
        """Validate questionnaire data."""
        if skip_validation:
            return True

        required_fields = ["gender", "marital_status", "region", "protest_participation"]
        if not all([profile_data.get(field) for field in required_fields]):
            st.error("אנא מלא/י את כל השדות הנדרשים או סמן/י 'דלג על שדות חובה'")
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
        """Render sidebar controls."""
        with st.sidebar:
            st.header("⚙️ הגדרות")

            # if st.button("🏠 תפריט ראשי"):
            #     st.session_state.app_mode = "main_menu"
            #     st.rerun()
            #
            # st.markdown("---")

            if st.button("🔙 חזרה לשאלון"):
                st.session_state.questionnaire_completed = False
                st.rerun()

            st.markdown("---")

            if st.button("✅ סיים שיחה"):
                st.session_state.conversation_finished = True
                st.rerun()

            # st.markdown("---")
            #
            # if st.button("🗑️ נקה היסטוריית שיחה"):
            #     self._clear_chat_history()
            #     st.rerun()

    def _render_chat_history(self) -> None:
        """Render chat history."""
        messages = st.session_state.get("messages", [])
        for message in messages:
            with st.chat_message(message["role"]):
                self.ui.render_rtl_message(message["content"])

    def _handle_user_input(self, prompt: str) -> None:
        """Handle user input and generate AI response."""
        # Add user message
        self._add_message("user", prompt)
        with st.chat_message("user"):
            self.ui.render_rtl_message(prompt)

        # Generate AI response
        with st.chat_message("assistant"):
            with self.ui.show_loading("🔍 מחפש מידע עדכני..."):
                user_profile = st.session_state.get("temp_user_profile")
                chat_context = self._get_chat_context()

                response_text = self.ai_service.generate_response(prompt, user_profile, chat_context)
                self.ui.render_rtl_message(response_text)
                self._add_message("assistant", response_text)

    def _render_conversation_summary(self) -> None:
        """Render conversation summary."""
        messages = st.session_state.get("messages", [])
        message_count = len(messages)
        user_messages = len([m for m in messages if m["role"] == "user"])

        st.markdown("### 📊 סיכום השיחה")
        self.ui.render_metrics([
            ("סך הודעות", message_count),
            ("הודעות משתמש", user_messages),
            ("הודעות בוט", message_count - user_messages)
        ])
        st.markdown("---")

    def _render_conversations_preview(self) -> None:
        """Render conversations preview for admin."""
        st.markdown("### 📋 תצוגת שיחות אחרונות")

        preview_data = self.data_service.get_conversations_preview()
        if preview_data:
            import pandas as pd
            df = pd.DataFrame(preview_data)
            df.columns = ['מזהה', 'זמן סיום', 'הודעות', 'אזור', 'גיל']
            st.dataframe(df, use_container_width=True)
        else:
            st.info("לא ניתן לטעון תצוגה מקדימה של השיחות")

    def _render_data_access_instructions(self) -> None:
        """Render data access instructions."""
        st.markdown("### 🔍 גישה מלאה לנתונים")
        st.markdown("""
        **לקבלת גישה מלאה לנתונים המחקריים:**
        1. גש ל-[Firebase Console](https://console.firebase.google.com)
        2. בחר את הפרויקט שלך
        3. עבור ל-Firestore Database
        4. כל השיחות נמצאות ב-collection: `conversations`
        5. ניתן לייצא לJSON או לחבר ל-Python/R לניתוח
        """)

    def _render_final_navigation(self) -> None:
        """Render final page navigation."""
        st.markdown("### 🔄 אפשרויות נוספות")
        col1, col2, col3 = st.columns(3)

        with col1:
            if st.button("🔙 חזרה לשאלון", use_container_width=True):
                self._reset_to_questionnaire()

        with col2:
            if st.button("🏠 תפריט ראשי", use_container_width=True):
                self._reset_to_main_menu()

        with col3:
            if st.button("🔄 התחל מחדש", use_container_width=True):
                self._reset_application()

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
        self._clear_chat_history()
        st.rerun()

    def _reset_application(self) -> None:
        """Reset entire application."""
        for key in list(st.session_state.keys()):
            del st.session_state[key]
        st.rerun()