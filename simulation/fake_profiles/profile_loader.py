"""
Loader for fake profile data from text files.
"""
import os
from typing import Dict, List, Any
import re
from pathlib import Path


class ProfileLoader:
    """Load and parse fake profiles from text files."""

    def __init__(self, profiles_dir: str = None):
        if profiles_dir is None:
            current_dir = Path(__file__).parent
            profiles_dir = current_dir / "profiles"
        self.profiles_dir = Path(profiles_dir)

    def load_all_profiles(self) -> Dict[str, Dict]:
        """Load all profiles from the profiles directory."""
        profiles = {}

        for file_path in self.profiles_dir.glob("*.txt"):
            profile_id = file_path.stem
            profile_data = self.load_profile(file_path)
            profiles[profile_id] = profile_data

        return profiles

    def load_profile(self, file_path: Path) -> Dict:
        """Load and parse a single profile file."""
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()

        profile = {}
        current_section = None

        for line in content.split('\n'):
            line = line.strip()

            # Skip comments and empty lines
            if not line or line.startswith('#'):
                continue

            # Section headers
            if line.endswith(':') and not ' ' in line[:-1]:
                current_section = line[:-1].lower()
                profile[current_section] = {}
                continue

            # Parse key-value pairs
            if ':' in line and current_section:
                key, value = line.split(':', 1)
                key = key.strip()
                value = value.strip()

                # Parse different value types
                if value.startswith('[') and value.endswith(']'):
                    # List
                    value = eval(value)
                elif value.isdigit():
                    # Integer
                    value = int(value)
                elif value == 'true':
                    value = True
                elif value == 'false':
                    value = False

                # Handle nested sections
                if current_section in ['feeling_thermometer_pre', 'social_distance_pre']:
                    profile[current_section][key] = value
                else:
                    if current_section not in profile:
                        profile[current_section] = {}
                    profile[current_section][key] = value

            # Handle list items (lines starting with -)
            elif line.startswith('- ') and current_section:
                item = line[2:].strip()
                # Find the last key in current section
                if current_section in profile and profile[current_section]:
                    last_key = list(profile[current_section].keys())[-1]
                    if not isinstance(profile[current_section][last_key], list):
                        profile[current_section][last_key] = [profile[current_section][last_key]]
                    profile[current_section][last_key].append(item)

        return profile

    def get_profile_by_stance(self, political_stance: str) -> List[Dict]:
        """Get all profiles with a specific political stance."""
        all_profiles = self.load_all_profiles()
        matching = []

        for profile_id, profile in all_profiles.items():
            if political_stance.lower() in profile_id.lower():
                profile['profile_id'] = profile_id
                matching.append(profile)

        return matching

    def convert_to_user_profile(self, profile_data: Dict) -> Dict:
        """Convert loaded profile to match UserProfile dataclass format."""

        basic = profile_data.get('basic_info', {})
        political = profile_data.get('political_behavior', {})
        civic = profile_data.get('civic_data', {})
        war = profile_data.get('war_position', {})

        return {
            # Demographics
            'gender': basic.get('gender', ''),
            'age': basic.get('age', 30),
            'marital_status': basic.get('marital_status', ''),
            'region': basic.get('region', ''),
            'religiosity': basic.get('religiosity', 1),
            'education': basic.get('education', ''),

            # Political
            'political_stance': basic.get('political_stance', 3),
            'last_election_vote': political.get('last_election_vote', ''),
            'polarization_perception': political.get('polarization_perception', ''),
            'protest_participation': political.get('protest_participation', ''),
            'military_service_recent': political.get('military_service_recent', ''),
            'influence_sources': civic.get('influence_sources', []),

            # Participation
            'voting_frequency': political.get('voting_frequency', ''),
            'political_discussions': political.get('political_discussions', ''),
            'social_media_activity': political.get('social_media_activity', ''),

            # Attitudes
            'trust_political_system': civic.get('trust_political_system', 5),
            'political_efficacy': civic.get('political_efficacy', 5),
            'political_anxiety': civic.get('political_anxiety', 5),

            # War positions
            'war_priority_pre': war.get('war_priority_pre', ''),
            'israel_action_pre': war.get('israel_action_pre', ''),

            # Complex measures
            'feeling_thermometer_pre': profile_data.get('feeling_thermometer_pre', {}),
            'social_distance_pre': profile_data.get('social_distance_pre', {}),
        }