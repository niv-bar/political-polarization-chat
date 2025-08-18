import streamlit as st
import json
import pandas as pd
from typing import List, Dict, Any, Optional
from services import DataService
from datetime import datetime


class DataExporter:
    """Enhanced utility class for viewing and exporting research data."""

    def __init__(self, data_service: DataService):
        self.data_service = data_service

    def render_data_viewer_section(self) -> None:
        """Render comprehensive data viewer with DataFrame and export options."""
        st.markdown("### 📊 צפייה וייצוא נתונים")

        # Get all conversation data
        with st.spinner("טוען נתונים..."):
            all_conversations = self._get_all_conversations()

        if not all_conversations:
            st.warning("אין נתונים זמינים")
            return

        # Convert to DataFrame for display
        df = self._create_analysis_dataframe(all_conversations)

        # Display data overview
        st.markdown(f"**סך הכל נמצאו {len(all_conversations)} שיחות**")

        # Tabs for different views
        tab1, tab2, tab3 = st.tabs(["📋 טבלת נתונים", "📊 סטטיסטיקות", "💾 ייצוא"])

        with tab1:
            self._render_dataframe_tab(df)

        with tab2:
            self._render_statistics_tab(df, all_conversations)

        with tab3:
            self._render_export_tab(df, all_conversations)

    def _render_dataframe_tab(self, df: pd.DataFrame) -> None:
        """Render the DataFrame viewing tab."""
        st.markdown("#### 🗂️ נתוני השיחות")

        # Filter options
        col1, col2, col3 = st.columns(3)

        with col1:
            # Region filter
            regions = ['הכל'] + list(df['region'].dropna().unique())
            selected_region = st.selectbox("סנן לפי אזור:", regions)

        with col2:
            # Age range filter
            min_age = int(df['age'].min()) if not df['age'].isna().all() else 18
            max_age = int(df['age'].max()) if not df['age'].isna().all() else 80
            age_range = st.slider("טווח גילאים:", min_age, max_age, (min_age, max_age))

        with col3:
            # Political stance filter
            political_range = st.slider("עמדה פוליטית:", 1, 10, (1, 10))

        # Apply filters
        filtered_df = df.copy()

        if selected_region != 'הכל':
            filtered_df = filtered_df[filtered_df['region'] == selected_region]

        filtered_df = filtered_df[
            (filtered_df['age'] >= age_range[0]) &
            (filtered_df['age'] <= age_range[1]) &
            (filtered_df['political_stance'] >= political_range[0]) &
            (filtered_df['political_stance'] <= political_range[1])
            ]

        st.markdown(f"**מציג {len(filtered_df)} שיחות (מתוך {len(df)})**")

        # Display DataFrame
        st.dataframe(
            filtered_df,
            use_container_width=True,
            hide_index=True,
            column_config={
                "session_id": st.column_config.TextColumn("מזהה", width="small"),
                "age": st.column_config.NumberColumn("גיל", width="small"),
                "gender": st.column_config.TextColumn("מגדר", width="small"),
                "region": st.column_config.TextColumn("אזור", width="medium"),
                "political_stance": st.column_config.NumberColumn("עמדה פוליטית", width="small"),
                "total_messages": st.column_config.NumberColumn("הודעות", width="small"),
                "duration_minutes": st.column_config.NumberColumn("משך (דק')", width="small")
            }
        )

    def _render_statistics_tab(self, df: pd.DataFrame, all_conversations: List[Dict]) -> None:
        """Render statistics tab."""
        st.markdown("#### 📈 סטטיסטיקות מחקריות")

        # Basic stats
        col1, col2, col3, col4 = st.columns(4)

        with col1:
            st.metric("סך שיחות", len(df))
        with col2:
            avg_age = df['age'].mean() if not df['age'].isna().all() else 0
            st.metric("ממוצע גיל", f"{avg_age:.1f}")
        with col3:
            avg_messages = df['total_messages'].mean() if not df['total_messages'].isna().all() else 0
            st.metric("ממוצע הודעות", f"{avg_messages:.1f}")
        with col4:
            avg_duration = df['duration_minutes'].mean() if not df['duration_minutes'].isna().all() else 0
            st.metric("ממוצע משך שיחה", f"{avg_duration:.1f} דק'")

        st.markdown("---")

        # Distribution charts
        col1, col2 = st.columns(2)

        with col1:
            st.markdown("**התפלגות לפי אזור:**")
            region_counts = df['region'].value_counts()
            st.bar_chart(region_counts)

        with col2:
            st.markdown("**התפלגות עמדה פוליטית:**")
            political_counts = df['political_stance'].value_counts().sort_index()
            st.bar_chart(political_counts)

        # Political stance statistics
        st.markdown("#### 🗳️ ניתוח עמדות פוליטיות")
        avg_political = df['political_stance'].mean() if not df['political_stance'].isna().all() else 0
        st.write(f"**ממוצע עמדה פוליטית:** {avg_political:.2f} (מתוך 10)")

        # Show political distribution
        left_leaning = len(df[df['political_stance'] <= 4])
        center = len(df[(df['political_stance'] > 4) & (df['political_stance'] < 7)])
        right_leaning = len(df[df['political_stance'] >= 7])

        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("נוטים שמאלה", f"{left_leaning} ({(left_leaning / len(df) * 100):.1f}%)")
        with col2:
            st.metric("מרכז", f"{center} ({(center / len(df) * 100):.1f}%)")
        with col3:
            st.metric("נוטים ימינה", f"{right_leaning} ({(right_leaning / len(df) * 100):.1f}%)")

    def _render_export_tab(self, df: pd.DataFrame, all_conversations: List[Dict]) -> None:
        """Render export options tab."""
        st.markdown("#### 💾 אפשרויות ייצוא")

        col1, col2 = st.columns(2)

        with col1:
            st.markdown("**ייצוא טבלת נתונים (CSV)**")
            st.markdown("מכיל נתונים דמוגרפיים ופוליטיים מסוכמים")

            csv_data = df.to_csv(index=False, encoding='utf-8-sig')
            st.download_button(
                label="📊 הורד CSV מסוכם",
                data=csv_data,
                file_name=f"political_research_summary_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
                mime="text/csv",
                use_container_width=True
            )

        with col2:
            st.markdown("**ייצוא נתונים מלאים (JSON)**")
            st.markdown("מכיל את כל השיחות המלאות והפרטים")

            export_data = {
                "export_timestamp": datetime.now().isoformat(),
                "total_conversations": len(all_conversations),
                "conversations": all_conversations
            }

            json_str = json.dumps(export_data, ensure_ascii=False, indent=2)
            st.download_button(
                label="📁 הורד JSON מלא",
                data=json_str,
                file_name=f"political_research_full_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json",
                mime="application/json",
                use_container_width=True
            )

        st.markdown("---")

        # Analysis report
        st.markdown("**דוח ניתוח מחקרי**")
        st.markdown("דוח מסוכם עם סטטיסטיקות ותובנות")

        if st.button("📈 צור והורד דוח ניתוח", use_container_width=True):
            report = self._generate_analysis_report(all_conversations, df)
            st.download_button(
                label="💾 הורד דוח ניתוח",
                data=report,
                file_name=f"political_research_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.md",
                mime="text/markdown"
            )

    def _create_analysis_dataframe(self, conversations: List[Dict[str, Any]]) -> pd.DataFrame:
        """Convert conversation data to analysis DataFrame."""
        rows = []

        for conv in conversations:
            profile = conv.get('user_profile', {})
            stats = conv.get('conversation_stats', {})

            row = {
                'session_id': conv.get('session_id', '')[:8],  # Shortened for display
                'created_at': conv.get('created_at', ''),
                'finished_at': conv.get('finished_at', ''),
                'age': profile.get('age', 0),
                'gender': profile.get('gender', ''),
                'region': profile.get('region', ''),
                'marital_status': profile.get('marital_status', ''),
                'religiosity': profile.get('religiosity', 0),
                'political_stance': profile.get('political_stance', 0),
                'protest_participation': profile.get('protest_participation', ''),
                'total_messages': stats.get('total_messages', 0),
                'user_messages': stats.get('user_messages', 0),
                'bot_messages': stats.get('bot_messages', 0),
                'duration_minutes': stats.get('duration_minutes', 0)
            }

            # Add feeling thermometer averages
            thermometer = profile.get('feeling_thermometer', {})
            if thermometer:
                row['avg_feeling_thermometer'] = sum(thermometer.values()) / len(thermometer)
                # Add individual party scores
                for party, score in thermometer.items():
                    row[f'feeling_{party}'] = score

            # Add social distance average
            social_dist = profile.get('social_distance', {})
            if social_dist:
                row['avg_social_distance'] = sum(social_dist.values()) / len(social_dist)
                # Add individual situation scores
                for situation, score in social_dist.items():
                    row[f'social_{situation}'] = score

            rows.append(row)

        df = pd.DataFrame(rows)

        # Convert timestamps to datetime for better display
        for col in ['created_at', 'finished_at']:
            if col in df.columns:
                df[col] = pd.to_datetime(df[col], errors='coerce')

        return df

    def _get_all_conversations(self) -> List[Dict[str, Any]]:
        """Get all conversations from the data service."""
        try:
            if hasattr(self.data_service, 'get_all_conversations'):
                return self.data_service.get_all_conversations()
            else:
                st.error("פונקציית ייצוא לא זמינה - נא לעדכן את שירות הנתונים")
                return []
        except Exception as e:
            st.error(f"שגיאה בטעינת נתונים: {str(e)}")
            return []

    def _generate_analysis_report(self, conversations: List[Dict[str, Any]], df: pd.DataFrame) -> str:
        """Generate comprehensive analysis report."""
        total_convs = len(conversations)

        if total_convs == 0:
            return "# דוח ניתוח מחקר קיטוב פוליטי\n\nאין נתונים זמינים לניתוח."

        # Calculate statistics
        avg_age = df['age'].mean() if not df['age'].isna().all() else 0
        avg_political = df['political_stance'].mean() if not df['political_stance'].isna().all() else 0
        avg_religiosity = df['religiosity'].mean() if not df['religiosity'].isna().all() else 0
        avg_messages = df['total_messages'].mean() if not df['total_messages'].isna().all() else 0
        avg_duration = df['duration_minutes'].mean() if not df['duration_minutes'].isna().all() else 0

        # Political distribution
        left_leaning = len(df[df['political_stance'] <= 4])
        center = len(df[(df['political_stance'] > 4) & (df['political_stance'] < 7)])
        right_leaning = len(df[df['political_stance'] >= 7])

        # Regional distribution
        region_counts = df['region'].value_counts()
        region_stats = "\n".join([f"- **{region}:** {count} ({(count / total_convs) * 100:.1f}%)"
                                  for region, count in region_counts.items()])

        # Gender distribution
        gender_counts = df['gender'].value_counts()
        gender_stats = "\n".join([f"- **{gender}:** {count} ({(count / total_convs) * 100:.1f}%)"
                                  for gender, count in gender_counts.items()])

        # Generate comprehensive report
        report = f"""# דוח ניתוח מחקר קיטוב פוליטי

## סיכום כלל
- **תאריך ייצוא:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
- **סך שיחות:** {total_convs}
- **סך הודעות:** {df['total_messages'].sum():.0f}

## נתונים דמוגרפיים

### גיל
- **ממוצע גיל:** {avg_age:.1f} שנים
- **גיל מינימלי:** {df['age'].min():.0f}
- **גיל מקסימלי:** {df['age'].max():.0f}

### התפלגות מגדר
{gender_stats}

### התפלגות אזורית
{region_stats}

## נתונים פוליטיים

### עמדה פוליטית
- **ממוצע עמדה פוליטית:** {avg_political:.2f} (מתוך 10)
- **נוטים שמאלה (1-4):** {left_leaning} ({(left_leaning / total_convs) * 100:.1f}%)
- **מרכז (5-6):** {center} ({(center / total_convs) * 100:.1f}%)
- **נוטים ימינה (7-10):** {right_leaning} ({(right_leaning / total_convs) * 100:.1f}%)

### רמת דתיות
- **ממוצע רמת דתיות:** {avg_religiosity:.2f} (מתוך 10)

## נתוני שיחות

### סטטיסטיקות שיחה
- **ממוצע הודעות לשיחה:** {avg_messages:.1f}
- **ממוצע משך שיחה:** {avg_duration:.1f} דקות
- **סך זמן שיחות:** {df['duration_minutes'].sum():.1f} דקות

### השתתפות בהפגנות
{self._get_protest_stats(df)}

## מדדי קיטוב

### מדי חום רגשי (ממוצע כלל המפלגות)
{self._get_feeling_thermometer_stats(conversations)}

### מרחק חברתי (ממוצע כלל המצבים)
{self._get_social_distance_stats(conversations)}

## המלצות למחקר

1. **גודל המדגם:** {total_convs} משתתפים מספק לניתוח ראשוני
2. **איזון דמוגרפי:** {'מאוזן יחסית' if self._check_demographic_balance(df) else 'דורש התאמה'}
3. **איכות נתונים:** {'גבוהה' if avg_messages >= 5 else 'בינונית'}

---
*דוח זה נוצר אוטומטית על ידי מערכת המחקר*
"""

        return report

    def _render_export_tab(self, df: pd.DataFrame, all_conversations: List[Dict]) -> None:
        """Render export options."""
        st.markdown("#### 💾 ייצוא נתונים")

        col1, col2 = st.columns(2)

        with col1:
            st.markdown("**ייצוא מהיר**")

            # Quick CSV export
            csv_data = df.to_csv(index=False, encoding='utf-8-sig')
            st.download_button(
                label="📊 הורד CSV (נתונים מעובדים)",
                data=csv_data,
                file_name=f"political_research_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
                mime="text/csv",
                use_container_width=True,
                help="קובץ CSV מעובד למחקר וניתוח סטטיסטי"
            )

        with col2:
            st.markdown("**ייצוא מתקדם**")

            # Full JSON export
            export_data = {
                "metadata": {
                    "export_timestamp": datetime.now().isoformat(),
                    "total_conversations": len(all_conversations),
                    "data_version": "1.0"
                },
                "conversations": all_conversations
            }

            json_str = json.dumps(export_data, ensure_ascii=False, indent=2)
            st.download_button(
                label="📁 הורד JSON (נתונים מלאים)",
                data=json_str,
                file_name=f"political_research_full_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json",
                mime="application/json",
                use_container_width=True,
                help="כולל את כל השיחות המלאות והפרטים"
            )

    def _get_protest_stats(self, df: pd.DataFrame) -> str:
        """Get protest participation statistics."""
        protest_counts = df['protest_participation'].value_counts()
        stats = []
        for participation, count in protest_counts.items():
            if participation:  # Skip empty values
                percentage = (count / len(df)) * 100
                stats.append(f"- **{participation}:** {count} ({percentage:.1f}%)")
        return "\n".join(stats) if stats else "- אין נתונים זמינים"

    def _get_feeling_thermometer_stats(self, conversations: List[Dict]) -> str:
        """Get feeling thermometer statistics."""
        try:
            all_scores = []
            for conv in conversations:
                thermometer = conv.get('user_profile', {}).get('feeling_thermometer', {})
                if thermometer:
                    all_scores.extend(thermometer.values())

            if all_scores:
                avg_score = sum(all_scores) / len(all_scores)
                return f"- **ממוצע כללי:** {avg_score:.1f} (מתוך 100)"
            else:
                return "- אין נתונים זמינים"
        except:
            return "- שגיאה בעיבוד נתונים"

    def _get_social_distance_stats(self, conversations: List[Dict]) -> str:
        """Get social distance statistics."""
        try:
            all_scores = []
            for conv in conversations:
                social_dist = conv.get('user_profile', {}).get('social_distance', {})
                if social_dist:
                    all_scores.extend(social_dist.values())

            if all_scores:
                avg_score = sum(all_scores) / len(all_scores)
                return f"- **ממוצע כללי:** {avg_score:.1f} (מתוך 6)"
            else:
                return "- אין נתונים זמינים"
        except:
            return "- שגיאה בעיבוד נתונים"

    def _check_demographic_balance(self, df: pd.DataFrame) -> bool:
        """Check if demographic distribution is reasonably balanced."""
        try:
            # Check age distribution
            age_std = df['age'].std()

            # Check regional distribution
            region_counts = df['region'].value_counts()
            region_balance = len(region_counts) >= 3  # At least 3 different regions

            # Check political distribution
            political_std = df['political_stance'].std()

            return age_std > 5 and region_balance and political_std > 1.5
        except:
            return False