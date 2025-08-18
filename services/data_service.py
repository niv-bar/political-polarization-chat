from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional
from models import UserProfile, ChatMessage


class DataService(ABC):
    """Abstract base class for data operations."""

    @abstractmethod
    def save_user_profile(self, profile: UserProfile) -> bool:
        """Save user profile to storage."""
        pass

    @abstractmethod
    def save_conversation(self, session_data: Dict[str, Any]) -> bool:
        """Save complete conversation data."""
        pass

    @abstractmethod
    def get_conversation_stats(self) -> Dict[str, Any]:
        """Get conversation statistics."""
        pass

    @abstractmethod
    def get_conversations_preview(self, limit: int = 10) -> List[Dict]:
        """Get preview of recent conversations."""
        pass

    @abstractmethod
    def get_all_conversations(self) -> List[Dict]:
        """Get all conversations."""
        pass