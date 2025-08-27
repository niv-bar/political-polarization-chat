from dataclasses import dataclass, field
from typing import List, Dict
import uuid
from datetime import datetime


@dataclass
class UserProfile:
    """Data class for user demographic and political profile - raw data only."""
    # Session Info
    session_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())

    # Demographic Data
    gender: str = ""
    age: int = 0
    marital_status: str = ""
    region: str = ""
    religiosity: int = 0
    education: str = ""

    # Political Data
    political_stance: int = 0
    last_election_vote: str = ""  # מי הצביע בבחירות האחרונות
    polarization_perception: str = ""  # תפיסת הקיטוב בשלוש השנים האחרונות
    protest_participation: str = ""
    influence_sources: List[str] = field(default_factory=list)

    # Political Participation
    voting_frequency: str = ""
    political_discussions: str = ""
    social_media_activity: str = ""

    # Political Attitudes - PRE-CHAT
    trust_political_system: int = 0
    political_efficacy: int = 0
    political_anxiety: int = 0
    feeling_thermometer_pre: Dict[str, int] = field(default_factory=dict)
    social_distance_pre: Dict[str, int] = field(default_factory=dict)

    # Political Attitudes - POST-CHAT
    trust_political_system_post: int = 0
    political_efficacy_post: int = 0
    feeling_thermometer_post: Dict[str, int] = field(default_factory=dict)
    social_distance_post: Dict[str, int] = field(default_factory=dict)

    # Post-chat reflection questions (open-ended text responses)
    conversation_impact: str = ""  # השפעת השיחה על דעותיך
    most_interesting: str = ""  # הדבר הכי מעניין בשיחה
    changed_mind: str = ""  # נושא שהשיחה גרמה לחשוב עליו אחרת

    # Legacy properties for backward compatibility
    @property
    def feeling_thermometer(self) -> Dict[str, int]:
        return self.feeling_thermometer_pre

    @property
    def social_distance(self) -> Dict[str, int]:
        return self.social_distance_pre