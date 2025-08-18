from dataclasses import dataclass
from datetime import datetime


@dataclass
class ChatMessage:
    """Data class for chat messages with automatic timestamp."""
    role: str
    content: str
    timestamp: str = None

    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = datetime.now().isoformat()

    def to_dict(self) -> dict:
        """Convert to dictionary for storage."""
        return {
            "role": self.role,
            "content": self.content,
            "timestamp": self.timestamp
        }