import streamlit as st
import json
import pandas as pd
from typing import List, Dict, Any, Optional
from services import DataService
from datetime import datetime
import io


class DataExporter:
    """Complete Firebase data viewer and exporter for political research."""

    def __init__(self, data_service: DataService):
        self.data_service = data_service

    def render_data_viewer_section(self) -> None:
        """Render complete data viewer with all Firebase data."""
        st.markdown("### 📊 צפייה וייצוא נתונים מלאים")

        # Get all conversation data from Firebase
        with st.spinner("טוען את כל הנתונים מ-Firebase..."):
            all_conversations = self._get_all_conversations()

        if not all_conversations:
            st.warning("אין נתונים זמינים במאגר")
            return

        # Convert to comprehensive DataFrame
        df = self._create_complete_dataframe(all_conversations)

        if df.empty:
            st.error("שגיאה ביצירת טבלת הנתונים")
            return

        # Display data overview
        st.success(f"**נטענו בהצלחה {len(all_conversations)} שיחות עם {len(df.columns)} עמודות נתונים**")

        # Main tabs
        tab1, tab2, tab3 = st.tabs(["📋 כל הנתונים", "📊 סטטיסטיקות מלאות", "💾 ייצוא מלא"])

        with tab1:
            self._render_complete_dataframe_tab(df, all_conversations)

        with tab2:
            self._render_complete_statistics_tab(df, all_conversations)

        with tab3:
            self._render_complete_export_tab(df, all_conversations)

    def _render_complete_dataframe_tab(self, df: pd.DataFrame, all_conversations: List[Dict]) -> None:
        """Render complete DataFrame with essential filters only."""
        st.markdown("#### 🗂️ כל נתוני המחקר")

        # Essential filters only
        col1, col2 = st.columns(2)

        with col1:
            # Region filter
            all_regions = df['region'].dropna().unique().tolist()
            regions = ['הכל'] + sorted([r for r in all_regions if r and r.strip()])
            selected_region = st.selectbox("סנן לפי אזור:", regions, key="region_filter")

        with col2:
            # Date range filter
            if not df['created_at'].isna().all():
                min_date = df['created_at'].min().date()
                max_date = df['created_at'].max().date()
                date_range = st.date_input(
                    "טווח תאריכים:",
                    value=(min_date, max_date),
                    min_value=min_date,
                    max_value=max_date,
                    key="date_filter"
                )
            else:
                date_range = None

        # Apply filters
        filtered_df = df.copy()

        if selected_region != 'הכל':
            filtered_df = filtered_df[filtered_df['region'] == selected_region]

        if date_range and len(date_range) == 2:
            start_date, end_date = date_range
            filtered_df = filtered_df[
                (filtered_df['created_at'].dt.date >= start_date) &
                (filtered_df['created_at'].dt.date <= end_date)
                ]

        st.markdown(f"**מציג {len(filtered_df)} שיחות (מתוך {len(df)})**")

        # Display complete DataFrame
        if not filtered_df.empty:
            # Reorder columns for better display
            display_columns = [
                'session_id', 'created_at', 'age', 'gender', 'region',
                'political_stance', 'last_election_vote', 'polarization_perception',
                'total_messages', 'duration_minutes', 'conversation_impact'
            ]

            # Add columns that exist
            final_columns = [col for col in display_columns if col in filtered_df.columns]
            remaining_columns = [col for col in filtered_df.columns if col not in final_columns]
            all_display_columns = final_columns + remaining_columns

            st.dataframe(
                filtered_df[all_display_columns],
                use_container_width=True,
                height=600,
                column_config={
                    "session_id": st.column_config.TextColumn("מזהה סשן", width="small"),
                    "created_at": st.column_config.DatetimeColumn("תאריך יצירה", width="medium"),
                    "age": st.column_config.NumberColumn("גיל", width="small"),
                    "gender": st.column_config.TextColumn("מגדר", width="small"),
                    "region": st.column_config.TextColumn("אזור", width="medium"),
                    "political_stance": st.column_config.NumberColumn("עמדה פוליטית", width="small"),
                    "last_election_vote": st.column_config.TextColumn("הצבעה אחרונה", width="medium"),
                    "polarization_perception": st.column_config.TextColumn("תפיסת קיטוב", width="medium"),
                    "total_messages": st.column_config.NumberColumn("סה\"כ הודעות", width="small"),
                    "duration_minutes": st.column_config.NumberColumn("משך (דק')", width="small"),
                    "conversation_impact": st.column_config.TextColumn("השפעת שיחה", width="medium")
                }
            )
        else:
            st.warning("אין נתונים המתאימים לסינון שנבחר")

    def _render_complete_statistics_tab(self, df: pd.DataFrame, all_conversations: List[Dict]) -> None:
        """Render comprehensive statistics for all data."""
        st.markdown("#### 📈 סטטיסטיקות מלאות לכל הנתונים")

        if df.empty:
            st.warning("אין נתונים לסטטיסטיקות")
            return

        # Overview metrics
        col1, col2, col3, col4 = st.columns(4)

        with col1:
            st.metric("סך השיחות", len(df))

        with col2:
            total_messages = df['total_messages'].sum() if 'total_messages' in df.columns else 0
            st.metric("סך ההודעות", f"{total_messages:,}")

        with col3:
            avg_duration = df['duration_minutes'].mean() if 'duration_minutes' in df.columns else 0
            st.metric("ממוצע משך שיחה", f"{avg_duration:.1f} דק'")

        with col4:
            total_duration = df['duration_minutes'].sum() if 'duration_minutes' in df.columns else 0
            st.metric("סך זמן שיחות", f"{total_duration:.0f} דק'")

        st.markdown("---")

        # Demographic statistics
        st.markdown("### 👥 נתונים דמוגרפיים")

        col1, col2 = st.columns(2)

        with col1:
            # Age statistics
            if 'age' in df.columns and not df['age'].isna().all():
                st.markdown("**התפלגות גילאים:**")
                age_stats = df['age'].describe()
                st.write(f"ממוצע: {age_stats['mean']:.1f}")
                st.write(f"חציון: {age_stats['50%']:.0f}")
                st.write(f"טווח: {age_stats['min']:.0f} - {age_stats['max']:.0f}")

                # Age distribution chart
                age_counts = df['age'].value_counts().sort_index()
                st.bar_chart(age_counts)

        with col2:
            # Gender distribution
            if 'gender' in df.columns:
                st.markdown("**התפלגות מגדר:**")
                gender_counts = df['gender'].value_counts()
                for gender, count in gender_counts.items():
                    if gender and gender.strip():
                        percentage = (count / len(df)) * 100
                        st.write(f"**{gender}:** {count} ({percentage:.1f}%)")
                st.bar_chart(gender_counts)

        # Regional distribution
        st.markdown("### 🗺️ התפלגות אזורית")
        if 'region' in df.columns:
            region_counts = df['region'].value_counts()
            col1, col2 = st.columns(2)

            with col1:
                for region, count in region_counts.items():
                    if region and region.strip():
                        percentage = (count / len(df)) * 100
                        st.write(f"**{region}:** {count} ({percentage:.1f}%)")

            with col2:
                st.bar_chart(region_counts)

        # Political data
        st.markdown("### 🗳️ נתונים פוליטיים")

        col1, col2 = st.columns(2)

        with col1:
            # Political stance distribution
            if 'political_stance' in df.columns and not df['political_stance'].isna().all():
                st.markdown("**עמדה פוליטית:**")
                avg_political = df['political_stance'].mean()
                st.write(f"ממוצע: {avg_political:.2f} (מתוך 5)")

                # Political categories
                left = len(df[df['political_stance'] <= 2])
                center = len(df[df['political_stance'] == 3])
                right = len(df[df['political_stance'] >= 4])
                total_valid = left + center + right

                if total_valid > 0:
                    st.write(f"**שמאל (1-2):** {left} ({(left / total_valid) * 100:.1f}%)")
                    st.write(f"**מרכז (3):** {center} ({(center / total_valid) * 100:.1f}%)")
                    st.write(f"**ימין (4-5):** {right} ({(right / total_valid) * 100:.1f}%)")

                political_counts = df['political_stance'].value_counts().sort_index()
                st.bar_chart(political_counts)

        with col2:
            # Last election vote
            if 'last_election_vote' in df.columns:
                st.markdown("**הצבעה בבחירות האחרונות:**")
                vote_counts = df['last_election_vote'].value_counts()
                for party, count in vote_counts.head(10).items():  # Show top 10
                    if party and party.strip():
                        percentage = (count / len(df)) * 100
                        st.write(f"**{party}:** {count} ({percentage:.1f}%)")

        # Polarization perception
        if 'polarization_perception' in df.columns:
            st.markdown("### 📊 תפיסת קיטוב פוליטי")
            polar_counts = df['polarization_perception'].value_counts()
            col1, col2 = st.columns(2)

            with col1:
                for perception, count in polar_counts.items():
                    if perception and perception.strip():
                        percentage = (count / len(df)) * 100
                        st.write(f"**{perception}:** {count} ({percentage:.1f}%)")

            with col2:
                st.bar_chart(polar_counts)

        # Conversation impact
        if 'conversation_impact' in df.columns:
            st.markdown("### 💭 השפעת השיחה")
            impact_counts = df['conversation_impact'].value_counts()
            col1, col2 = st.columns(2)

            with col1:
                for impact, count in impact_counts.items():
                    if impact and impact.strip():
                        percentage = (count / len(df)) * 100
                        st.write(f"**{impact}:** {count} ({percentage:.1f}%)")

            with col2:
                st.bar_chart(impact_counts)

    def _render_complete_export_tab(self, df: pd.DataFrame, all_conversations: List[Dict]) -> None:
        """Render complete export options for all data."""
        st.markdown("#### 💾 ייצוא מלא של כל הנתונים")

        col1, col2 = st.columns(2)

        with col1:
            st.markdown("**📊 ייצוא CSV מלא (עם עברית)**")
            st.markdown("כולל את כל הנתונים בפורמט מובנה עם תמיכה מלאה בעברית")

            # Create Hebrew-friendly CSV
            hebrew_csv = self._create_hebrew_csv(df)

            st.download_button(
                label="📥 הורד CSV מלא בעברית",
                data=hebrew_csv,
                file_name=f"מחקר_פוליטי_מלא_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
                mime="text/csv",
                use_container_width=True,
                help="קובץ CSV עם כל הנתונים, מותאם לעברית"
            )

        with col2:
            st.markdown("**📁 ייצוא JSON מלא**")
            st.markdown("כולל את כל השיחות המלאות, הפרופילים והמטאדאטה")

            # Create complete JSON export
            complete_export = self._create_complete_json(all_conversations)

            st.download_button(
                label="📥 הורד JSON מלא",
                data=complete_export,
                file_name=f"מחקר_פוליטי_JSON_מלא_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json",
                mime="application/json",
                use_container_width=True,
                help="קובץ JSON עם כל השיחות, ההודעות והנתונים"
            )

        st.markdown("---")

        # Summary report
        st.markdown("**📋 דוח סיכום מלא**")
        st.markdown("דוח מפורט עם כל הסטטיסטיקות והממצאים")

        if st.button("📈 צור דוח סיכום מלא", use_container_width=True):
            report = self._generate_complete_report(df, all_conversations)

            st.download_button(
                label="📥 הורד דוח מלא",
                data=report,
                file_name=f"דוח_מחקר_פוליטי_מלא_{datetime.now().strftime('%Y%m%d_%H%M%S')}.md",
                mime="text/markdown",
                use_container_width=True
            )

    def _create_complete_dataframe(self, conversations: List[Dict[str, Any]]) -> pd.DataFrame:
        """Create comprehensive DataFrame with all available data."""
        if not conversations:
            return pd.DataFrame()

        rows = []

        for conv in conversations:
            try:
                profile = conv.get('user_profile', {})
                stats = conv.get('conversation_stats', {})

                # Basic session info
                row = {
                    'session_id': str(conv.get('session_id', ''))[:12],
                    'created_at': conv.get('created_at', ''),
                    'finished_at': conv.get('finished_at', ''),
                }

                # Demographic data
                row.update({
                    'age': self._safe_int(profile.get('age')),
                    'gender': profile.get('gender', ''),
                    'region': profile.get('region', ''),
                    'marital_status': profile.get('marital_status', ''),
                    'education': profile.get('education', ''),
                    'religiosity': self._safe_int(profile.get('religiosity')),
                })

                # Political data
                row.update({
                    'political_stance': self._safe_int(profile.get('political_stance')),
                    'last_election_vote': profile.get('last_election_vote', ''),
                    'polarization_perception': profile.get('polarization_perception', ''),
                    'voting_frequency': profile.get('voting_frequency', ''),
                    'protest_participation': profile.get('protest_participation', ''),
                    'political_discussions': profile.get('political_discussions', ''),
                    'social_media_activity': profile.get('social_media_activity', ''),
                })

                # Attitude measures - PRE
                row.update({
                    'trust_political_system_pre': self._safe_int(profile.get('trust_political_system')),
                    'political_efficacy_pre': self._safe_int(profile.get('political_efficacy')),
                    'political_anxiety': self._safe_int(profile.get('political_anxiety')),
                })

                # Attitude measures - POST
                row.update({
                    'trust_political_system_post': self._safe_int(profile.get('trust_political_system_post')),
                    'political_efficacy_post': self._safe_int(profile.get('political_efficacy_post')),
                })

                # Post-chat reflection
                row.update({
                    'conversation_impact': profile.get('conversation_impact', ''),
                    'most_interesting': profile.get('most_interesting', ''),
                    'changed_mind': profile.get('changed_mind', ''),
                })

                # Conversation stats
                row.update({
                    'total_messages': self._safe_int(stats.get('total_messages')),
                    'user_messages': self._safe_int(stats.get('user_messages')),
                    'bot_messages': self._safe_int(stats.get('bot_messages')),
                    'duration_minutes': self._safe_float(stats.get('duration_minutes')),
                })

                # Information sources
                influence_sources = profile.get('influence_sources', [])
                if isinstance(influence_sources, list):
                    row['influence_sources'] = '; '.join(influence_sources)
                else:
                    row['influence_sources'] = str(influence_sources) if influence_sources else ''

                # Feeling thermometer data
                thermometer_pre = profile.get('feeling_thermometer_pre', {}) or profile.get('feeling_thermometer', {})
                thermometer_post = profile.get('feeling_thermometer_post', {})

                if isinstance(thermometer_pre, dict):
                    for party, score in thermometer_pre.items():
                        row[f'feeling_pre_{party}'] = self._safe_int(score)

                if isinstance(thermometer_post, dict):
                    for party, score in thermometer_post.items():
                        row[f'feeling_post_{party}'] = self._safe_int(score)

                # Social distance data
                social_pre = profile.get('social_distance_pre', {}) or profile.get('social_distance', {})
                social_post = profile.get('social_distance_post', {})

                if isinstance(social_pre, dict):
                    for situation, score in social_pre.items():
                        row[f'social_pre_{situation}'] = self._safe_int(score)

                if isinstance(social_post, dict):
                    for situation, score in social_post.items():
                        row[f'social_post_{situation}'] = self._safe_int(score)

                rows.append(row)

            except Exception as e:
                st.warning(f"שגיאה בעיבוד שיחה {conv.get('session_id', 'unknown')}: {str(e)[:100]}...")
                continue

        if not rows:
            return pd.DataFrame()

        df = pd.DataFrame(rows)

        # Convert timestamps
        for col in ['created_at', 'finished_at']:
            if col in df.columns:
                df[col] = pd.to_datetime(df[col], errors='coerce')

        return df

    def _create_hebrew_csv(self, df: pd.DataFrame) -> bytes:
        """Create CSV with proper Hebrew encoding and headers."""
        if df.empty:
            return "אין נתונים זמינים".encode('utf-8-sig')

        # Hebrew column mapping
        hebrew_columns = {
            'session_id': 'מזהה_סשן',
            'created_at': 'תאריך_יצירה',
            'finished_at': 'תאריך_סיום',
            'age': 'גיל',
            'gender': 'מגדר',
            'region': 'אזור',
            'marital_status': 'מצב_משפחתי',
            'education': 'השכלה',
            'religiosity': 'דתיות',
            'political_stance': 'עמדה_פוליטית',
            'last_election_vote': 'הצבעה_אחרונה',
            'polarization_perception': 'תפיסת_קיטוב',
            'voting_frequency': 'תדירות_הצבעה',
            'protest_participation': 'השתתפות_הפגנות',
            'political_discussions': 'דיונים_פוליטיים',
            'social_media_activity': 'פעילות_רשתות',
            'trust_political_system_pre': 'אמון_מערכת_לפני',
            'trust_political_system_post': 'אמון_מערכת_אחרי',
            'political_efficacy_pre': 'השפעה_פוליטית_לפני',
            'political_efficacy_post': 'השפעה_פוליטית_אחרי',
            'political_anxiety': 'חרדה_פוליטית',
            'conversation_impact': 'השפעת_שיחה',
            'most_interesting': 'הכי_מעניין',
            'changed_mind': 'שינוי_דעה',
            'total_messages': 'סך_הודעות',
            'user_messages': 'הודעות_משתמש',
            'bot_messages': 'הודעות_בוט',
            'duration_minutes': 'משך_דקות',
            'influence_sources': 'מקורות_מידע'
        }

        # Create DataFrame copy with Hebrew columns
        df_hebrew = df.copy()

        # Rename columns to Hebrew where mapping exists
        for eng_col, heb_col in hebrew_columns.items():
            if eng_col in df_hebrew.columns:
                df_hebrew = df_hebrew.rename(columns={eng_col: heb_col})

        # Convert to CSV with proper encoding
        buffer = io.StringIO()
        df_hebrew.to_csv(buffer, index=False, encoding='utf-8')
        return buffer.getvalue().encode('utf-8-sig')

    def _create_complete_json(self, conversations: List[Dict]) -> str:
        """Create complete JSON export with all data."""
        export_data = {
            "metadata": {
                "export_timestamp": datetime.now().isoformat(),
                "total_conversations": len(conversations),
                "data_version": "2.0",
                "description": "מחקר קיטוב פוליטי - ייצוא מלא",
                "fields_included": [
                    "user_profiles", "conversations", "session_info",
                    "demographic_data", "political_data", "attitude_measures",
                    "feeling_thermometer", "social_distance", "reflection_responses"
                ]
            },
            "conversations": conversations,
            "summary": {
                "total_participants": len(conversations),
                "export_date": datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                "total_messages": sum(
                    conv.get('conversation_stats', {}).get('total_messages', 0)
                    for conv in conversations
                )
            }
        }

        return json.dumps(export_data, ensure_ascii=False, indent=2)

    def _generate_complete_report(self, df: pd.DataFrame, conversations: List[Dict]) -> str:
        """Generate comprehensive research report."""
        if df.empty:
            return "# דוח מחקר קיטוב פוליטי\n\nאין נתונים זמינים."

        total_participants = len(conversations)

        # Calculate comprehensive statistics
        stats = self._calculate_comprehensive_stats(df)

        report = f"""# דוח מחקר קיטוב פוליטי - ניתוח מלא

## מטאדאטה
- **תאריך ייצוא:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
- **סך המשתתפים:** {total_participants:,}
- **סך ההודעות:** {stats['total_messages']:,}
- **סך זמן השיחות:** {stats['total_duration']:.0f} דקות ({stats['total_duration'] / 60:.1f} שעות)

## נתונים דמוגרפיים

### גיל
- **ממוצע:** {stats['age_mean']:.1f} שנים
- **חציון:** {stats['age_median']:.0f} שנים
- **טווח:** {stats['age_min']:.0f} - {stats['age_max']:.0f} שנים

### מגדר
{stats['gender_distribution']}

### התפלגות אזורית
{stats['region_distribution']}

### השכלה
{stats['education_distribution']}

### דתיות
- **ממוצע רמת דתיות:** {stats['religiosity_mean']:.2f} (מתוך 4)

## נתונים פוליטיים

### עמדה פוליטית
- **ממוצע:** {stats['political_mean']:.2f} (מתוך 5)
- **התפלגות:**
{stats['political_distribution']}

### הצבעה בבחירות האחרונות
{stats['election_vote_distribution']}

### תפיסת קיטוב פוליטי
{stats['polarization_distribution']}

## מדדי עמדות

### אמון במערכת הפוליטית
- **לפני השיחה:** {stats['trust_pre_mean']:.2f}
- **אחרי השיחה:** {stats['trust_post_mean']:.2f}
- **שינוי ממוצע:** {stats['trust_change']:.2f}

### תחושת השפעה פוליטית
- **לפני השיחה:** {stats['efficacy_pre_mean']:.2f}
- **אחרי השיחה:** {stats['efficacy_post_mean']:.2f}
- **שינוי ממוצע:** {stats['efficacy_change']:.2f}

## השפעת השיחה
{stats['conversation_impact_distribution']}

## סטטיסטיקות שיחה
- **ממוצע הודעות לשיחה:** {stats['avg_messages']:.1f}
- **ממוצע הודעות משתמש:** {stats['avg_user_messages']:.1f}
- **ממוצע משך שיחה:** {stats['avg_duration']:.1f} דקות

## תובנות מרכזיות

{self._generate_insights(stats)}

---
*דוח זה נוצר אוטומטית ממערכת ניהול נתוני המחקר*
"""

        return report

    def _calculate_comprehensive_stats(self, df: pd.DataFrame) -> Dict[str, Any]:
        """Calculate comprehensive statistics for the report."""
        stats = {}

        # Basic counts
        stats['total_messages'] = df['total_messages'].sum() if 'total_messages' in df.columns else 0
        stats['total_duration'] = df['duration_minutes'].sum() if 'duration_minutes' in df.columns else 0
        stats['avg_messages'] = df['total_messages'].mean() if 'total_messages' in df.columns else 0
        stats['avg_user_messages'] = df['user_messages'].mean() if 'user_messages' in df.columns else 0
        stats['avg_duration'] = df['duration_minutes'].mean() if 'duration_minutes' in df.columns else 0

        # Age statistics
        if 'age' in df.columns:
            age_data = df['age'].dropna()
            stats['age_mean'] = age_data.mean() if not age_data.empty else 0
            stats['age_median'] = age_data.median() if not age_data.empty else 0
            stats['age_min'] = age_data.min() if not age_data.empty else 0
            stats['age_max'] = age_data.max() if not age_data.empty else 0
        else:
            stats.update({'age_mean': 0, 'age_median': 0, 'age_min': 0, 'age_max': 0})

        # Political stance statistics
        if 'political_stance' in df.columns:
            political_data = df['political_stance'].dropna()
            stats['political_mean'] = political_data.mean() if not political_data.empty else 0
        else:
            stats['political_mean'] = 0

        # Religiosity
        if 'religiosity' in df.columns:
            religiosity_data = df['religiosity'].dropna()
            stats['religiosity_mean'] = religiosity_data.mean() if not religiosity_data.empty else 0
        else:
            stats['religiosity_mean'] = 0

        # Attitude changes
        if 'trust_political_system_pre' in df.columns:
            trust_pre = df['trust_political_system_pre'].dropna().mean()
            trust_post = df[
                'trust_political_system_post'].dropna().mean() if 'trust_political_system_post' in df.columns else trust_pre
            stats['trust_pre_mean'] = trust_pre
            stats['trust_post_mean'] = trust_post
            stats['trust_change'] = trust_post - trust_pre
        else:
            stats.update({'trust_pre_mean': 0, 'trust_post_mean': 0, 'trust_change': 0})

        if 'political_efficacy_pre' in df.columns:
            efficacy_pre = df['political_efficacy_pre'].dropna().mean()
            efficacy_post = df[
                'political_efficacy_post'].dropna().mean() if 'political_efficacy_post' in df.columns else efficacy_pre
            stats['efficacy_pre_mean'] = efficacy_pre
            stats['efficacy_post_mean'] = efficacy_post
            stats['efficacy_change'] = efficacy_post - efficacy_pre
        else:
            stats.update({'efficacy_pre_mean': 0, 'efficacy_post_mean': 0, 'efficacy_change': 0})

        # Distribution strings
        stats['gender_distribution'] = self._create_distribution_string(df, 'gender')
        stats['region_distribution'] = self._create_distribution_string(df, 'region')
        stats['education_distribution'] = self._create_distribution_string(df, 'education')
        stats['political_distribution'] = self._create_political_distribution(df)
        stats['election_vote_distribution'] = self._create_distribution_string(df, 'last_election_vote', limit=10)
        stats['polarization_distribution'] = self._create_distribution_string(df, 'polarization_perception')
        stats['conversation_impact_distribution'] = self._create_distribution_string(df, 'conversation_impact')

        return stats

    def _create_distribution_string(self, df: pd.DataFrame, column: str, limit: int = None) -> str:
        """Create distribution string for a column."""
        if column not in df.columns:
            return "- אין נתונים זמינים"

        counts = df[column].value_counts()
        if limit:
            counts = counts.head(limit)

        result = []
        total = len(df)
        for value, count in counts.items():
            if value and str(value).strip():
                percentage = (count / total) * 100
                result.append(f"- **{value}:** {count} ({percentage:.1f}%)")

        return "\n".join(result) if result else "- אין נתונים זמינים"

    def _create_political_distribution(self, df: pd.DataFrame) -> str:
        """Create political stance distribution."""
        if 'political_stance' not in df.columns:
            return "- אין נתונים זמינים"

        political_data = df['political_stance'].dropna()
        if political_data.empty:
            return "- אין נתונים זמינים"

        left = len(political_data[political_data <= 2])
        center = len(political_data[political_data == 3])
        right = len(political_data[political_data >= 4])
        total = len(political_data)

        return f"""- **שמאל (1-2):** {left} ({(left / total) * 100:.1f}%)
- **מרכז (3):** {center} ({(center / total) * 100:.1f}%)
- **ימין (4-5):** {right} ({(right / total) * 100:.1f}%)"""

    def _generate_insights(self, stats: Dict[str, Any]) -> str:
        """Generate key insights from the data."""
        insights = []

        if stats['trust_change'] != 0:
            direction = "עלה" if stats['trust_change'] > 0 else "ירד"
            insights.append(f"• האמון במערכת הפוליטית {direction} בממוצע של {abs(stats['trust_change']):.2f} נקודות")

        if stats['efficacy_change'] != 0:
            direction = "עלתה" if stats['efficacy_change'] > 0 else "ירדה"
            insights.append(f"• תחושת ההשפעה הפוליטית {direction} בממוצע של {abs(stats['efficacy_change']):.2f} נקודות")

        if stats['avg_duration'] > 0:
            quality = "גבוהה" if stats['avg_duration'] >= 10 else "בינונית" if stats['avg_duration'] >= 5 else "נמוכה"
            insights.append(f"• איכות המעורבות בשיחות: {quality} (ממוצע {stats['avg_duration']:.1f} דקות)")

        if stats['avg_messages'] > 0:
            engagement = "גבוהה" if stats['avg_messages'] >= 10 else "בינונית" if stats[
                                                                                      'avg_messages'] >= 5 else "נמוכה"
            insights.append(f"• רמת מעורבות בשיחות: {engagement} (ממוצע {stats['avg_messages']:.1f} הודעות)")

        return "\n".join(insights) if insights else "• לא זוהו דפוסים משמעותיים בנתונים"

    def _safe_int(self, value) -> int:
        """Safely convert value to int."""
        try:
            if value is None or value == '' or pd.isna(value):
                return 0
            return int(float(value))
        except (ValueError, TypeError):
            return 0

    def _safe_float(self, value) -> float:
        """Safely convert value to float."""
        try:
            if value is None or value == '' or pd.isna(value):
                return 0.0
            return float(value)
        except (ValueError, TypeError):
            return 0.0

    def _get_all_conversations(self) -> List[Dict[str, Any]]:
        """Get all conversations from Firebase."""
        try:
            if hasattr(self.data_service, 'get_all_conversations'):
                return self.data_service.get_all_conversations()
            else:
                st.error("פונקציית טעינת נתונים לא זמינה - נא לעדכן את שירות הנתונים")
                return []
        except Exception as e:
            st.error(f"שגיאה בטעינת נתונים מ-Firebase: {str(e)}")
            return []