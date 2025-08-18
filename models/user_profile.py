from dataclasses import dataclass, field
from typing import List, Dict
import uuid
from datetime import datetime

@dataclass
class UserProfile:
    """Data class for user demographic and political profile."""
    # Session Info
    session_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())

    # Demographic Data
    gender: str = ""
    age: int = 0
    marital_status: str = ""
    region: str = ""
    religiosity: int = 0

    # Political Data
    political_stance: int = 0
    protest_participation: str = ""
    influence_sources: List[str] = field(default_factory=list)

    # Polarization Measurements
    feeling_thermometer: Dict[str, int] = field(default_factory=dict)
    social_distance: Dict[str, int] = field(default_factory=dict)