"""
Controls the experiment execution with balanced allocation.
"""
import random
import json
import time
from typing import Dict, List, Tuple
from pathlib import Path
from datetime import datetime
import itertools

from .conversation_simulator import ConversationSimulator
from .rate_limiter import GeminiRateLimiter
from .fake_profiles.profile_loader import ProfileLoader


class ExperimentController:
    """
    Manages the full experiment with balanced allocation.
    10 profiles × 3 interventions = 30 conversations total.
    """

    def __init__(self, gemini_api_key: str, output_dir: str = "simulation/results"):
        self.simulator = ConversationSimulator(gemini_api_key)
        self.rate_limiter = GeminiRateLimiter()
        self.profile_loader = ProfileLoader()
        self.output_dir = Path(output_dir)

        # Create output directories
        self.output_dir.mkdir(parents=True, exist_ok=True)
        (self.output_dir / "conversations").mkdir(exist_ok=True)
        (self.output_dir / "logs").mkdir(exist_ok=True)

        # Intervention types
        self.interventions = ["shared_identity", "misperception_correction", "control"]

    def run_experiment(self,
                       test_mode: bool = False,
                       specific_profiles: List[str] = None) -> Dict:
        """
        Run the complete experiment.

        Args:
            test_mode: If True, only run 3 conversations for testing
            specific_profiles: List of specific profile IDs to use
        """

        print("=" * 50)
        print("Starting Experiment")
        print("=" * 50)

        # Load profiles
        all_profiles = self.profile_loader.load_all_profiles()

        if specific_profiles:
            profiles_to_use = {k: v for k, v in all_profiles.items()
                               if k in specific_profiles}
        elif test_mode:
            # In test mode, use one profile from each stance
            profiles_to_use = {}
            for stance in ["left", "center_left", "center"]:
                stance_profiles = {k: v for k, v in all_profiles.items()
                                   if stance in k}
                if stance_profiles:
                    profiles_to_use.update({list(stance_profiles.keys())[0]:
                                                list(stance_profiles.values())[0]})
        else:
            profiles_to_use = all_profiles

        print(f"Loaded {len(profiles_to_use)} profiles")

        # Create all combinations
        combinations = list(itertools.product(
            profiles_to_use.items(),
            self.interventions
        ))

        # Randomize order
        random.shuffle(combinations)

        # Limit combinations in test mode
        if test_mode:
            combinations = combinations[:3]

        print(f"Will run {len(combinations)} conversations")
        print("-" * 50)

        # Track results
        results = {
            'successful': [],
            'failed': [],
            'metadata': {
                'start_time': datetime.now().isoformat(),
                'total_planned': len(combinations),
                'test_mode': test_mode
            }
        }

        # Run conversations
        for i, ((profile_id, profile_data), intervention) in enumerate(combinations, 1):
            print(f"\n[{i}/{len(combinations)}] Running: {profile_id} × {intervention}")

            # Add profile_id to profile data
            profile_data['profile_id'] = profile_id

            try:
                # Check rate limit
                self.rate_limiter.wait_if_needed(estimated_tokens=2000)

                # Run conversation
                conversation_result = self.simulator.simulate_conversation(
                    profile_data=profile_data,
                    intervention_type=intervention
                )

                # Save conversation
                save_path = self.simulator.save_conversation(
                    conversation_result,
                    output_dir=str(self.output_dir)
                )

                # Record success
                results['successful'].append({
                    'profile_id': profile_id,
                    'intervention': intervention,
                    'message_count': len(conversation_result['conversation']),
                    'file_path': str(save_path)
                })

                # Record API usage
                self.rate_limiter.record_request(tokens_used=2000)

                print(f"✓ Success: {len(conversation_result['conversation'])} messages")

                # Add delay between conversations
                if i < len(combinations):
                    if i % 5 == 0:
                        print("\n⏸ Pausing for 60 seconds to avoid rate limits...")
                        time.sleep(60)
                    else:
                        time.sleep(5)  # Small delay between all conversations

            except Exception as e:
                print(f"✗ Failed: {str(e)}")

                # Record failure
                results['failed'].append({
                    'profile_id': profile_id,
                    'intervention': intervention,
                    'error': str(e)
                })

                # Save partial results if too many failures
                if len(results['failed']) >= 3:
                    print("\n⚠ Multiple failures detected. Saving partial results...")
                    self._save_experiment_log(results)

                # Handle rate limit errors
                if "rate limit" in str(e).lower():
                    print("⏸ Rate limit hit. Waiting 5 minutes...")
                    time.sleep(300)

        # Complete experiment
        results['metadata']['end_time'] = datetime.now().isoformat()
        results['metadata']['total_successful'] = len(results['successful'])
        results['metadata']['total_failed'] = len(results['failed'])

        # Save final log
        self._save_experiment_log(results)

        # Print summary
        self._print_summary(results)

        return results

    def _save_experiment_log(self, results: Dict) -> None:
        """Save experiment log to file."""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        log_path = self.output_dir / "logs" / f"experiment_log_{timestamp}.json"

        with open(log_path, 'w', encoding='utf-8') as f:
            json.dump(results, f, ensure_ascii=False, indent=2)

        print(f"Log saved to {log_path}")

    def _print_summary(self, results: Dict) -> None:
        """Print experiment summary."""
        print("\n" + "=" * 50)
        print("EXPERIMENT SUMMARY")
        print("=" * 50)

        print(f"Total conversations: {results['metadata']['total_planned']}")
        print(f"Successful: {results['metadata']['total_successful']}")
        print(f"Failed: {results['metadata']['total_failed']}")

        if results['successful']:
            avg_messages = sum(r['message_count'] for r in results['successful']) / len(results['successful'])
            print(f"Average message count: {avg_messages:.1f}")

        # Count by intervention
        if results['successful']:
            print("\nBy intervention:")
            for intervention in self.interventions:
                count = sum(1 for r in results['successful']
                            if r['intervention'] == intervention)
                print(f"  {intervention}: {count}")

        print("\nResults saved to:", self.output_dir)

    def validate_balance(self, results: Dict) -> Dict:
        """Validate that the allocation is balanced."""
        successful = results['successful']

        # Count combinations
        combination_counts = {}
        for result in successful:
            key = f"{result['profile_id'].split('_')[0]}_{result['intervention']}"
            combination_counts[key] = combination_counts.get(key, 0) + 1

        # Check balance
        counts = list(combination_counts.values())
        is_balanced = len(set(counts)) <= 2  # Allow for small variation

        return {
            'is_balanced': is_balanced,
            'combination_counts': combination_counts,
            'unique_counts': list(set(counts))
        }