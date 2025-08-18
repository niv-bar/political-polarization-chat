import streamlit as st
import firebase_admin
from firebase_admin import credentials, firestore
from typing import Dict, Any, List, Optional
import os
from .data_service import DataService
from models import UserProfile


class FirebaseService(DataService):
    """Firebase implementation of data service."""

    def __init__(self):
        self.db = None
        self._initialize_firebase()

    def _initialize_firebase(self):
        """Initialize Firebase Admin SDK."""
        try:
            if not firebase_admin._apps:
                if "firebase" in st.secrets:
                    firebase_creds = dict(st.secrets["firebase"])
                    cred = credentials.Certificate(firebase_creds)
                    firebase_admin.initialize_app(cred)
                elif os.path.exists("firebase-key.json"):
                    cred = credentials.Certificate("firebase-key.json")
                    firebase_admin.initialize_app(cred)
                else:
                    st.error("❌ לא נמצאו אישורי Firebase")
                    return

            self.db = firestore.client()

        except Exception as e:
            st.error(f"❌ שגיאה באתחול Firebase: {str(e)}")
            self.db = None

    def save_user_profile(self, profile: UserProfile) -> bool:
        """Save user profile to Firestore."""
        try:
            if not self.db:
                return False

            doc_ref = self.db.collection('profiles').document(profile.session_id)
            doc_ref.set(profile.__dict__)
            return True

        except Exception as e:
            st.error(f"❌ שגיאה בשמירת פרופיל: {str(e)}")
            return False

    def save_conversation(self, session_data: Dict[str, Any]) -> bool:
        """Save conversation data to Firestore."""
        try:
            if not self.db:
                st.error("❌ מסד הנתונים לא מוכן")
                return False

            doc_ref = self.db.collection('conversations').document(session_data['session_id'])
            doc_ref.set(session_data)
            st.success("✅ הנתונים נשמרו בהצלחה למסד הנתונים!")
            return True

        except Exception as e:
            st.error(f"❌ שגיאה בשמירת הנתונים: {str(e)}")
            return False

    def get_conversation_stats(self) -> Dict[str, Any]:
        """Get conversation statistics."""
        try:
            if not self.db:
                return {"total_conversations": 0}

            conversations = self.db.collection('conversations').stream()
            total = len(list(conversations))

            return {
                "total_conversations": total,
                "completion_rate": f"{(total / 300) * 100:.1f}%" if total > 0 else "0%"
            }

        except Exception:
            return {"total_conversations": 0}

    def get_conversations_preview(self, limit: int = 10) -> List[Dict]:
        """Get preview of recent conversations."""
        try:
            if not self.db:
                return []

            conversations = (self.db.collection('conversations')
                             .order_by('finished_at', direction=firestore.Query.DESCENDING)
                             .limit(limit)
                             .stream())

            preview = []
            for conv in conversations:
                data = conv.to_dict()
                preview.append({
                    'session_id': data.get('session_id', '')[:8],
                    'finished_at': data.get('finished_at', ''),
                    'total_messages': data.get('conversation_stats', {}).get('total_messages', 0),
                    'user_region': data.get('user_profile', {}).get('region', 'לא צוין'),
                    'user_age': data.get('user_profile', {}).get('age', 0)
                })

            return preview

        except Exception:
            return []

    def get_all_conversations(self) -> List[Dict]:
        """Get all conversations from Firestore."""
        try:
            if not self.db:
                return []

            conversations = self.db.collection('conversations').stream()
            all_convs = []

            for conv in conversations:
                all_convs.append(conv.to_dict())

            return all_convs

        except Exception as e:
            st.error(f"Error fetching conversations: {str(e)}")
            return []