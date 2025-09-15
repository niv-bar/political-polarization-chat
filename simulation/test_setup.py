"""
Test script to verify the simulation setup is working.
"""
import sys
from pathlib import Path

# Add parent directory to path
sys.path.append(str(Path(__file__).parent.parent))


def test_imports():
    """Test that all imports work."""
    print("Testing imports...")

    try:
        from simulation.fake_profiles.profile_loader import ProfileLoader
        print("✓ ProfileLoader imported")

        from simulation.interventions import INTERVENTIONS
        print("✓ Interventions imported")

        from simulation.conversation_simulator import ConversationSimulator
        print("✓ ConversationSimulator imported")

        from simulation.rate_limiter import GeminiRateLimiter
        print("✓ RateLimiter imported")

        from simulation.experiment_controller import ExperimentController
        print("✓ ExperimentController imported")

        from simulation.metrics_analyzer import MetricsAnalyzer
        print("✓ MetricsAnalyzer imported")

    except ImportError as e:
        print(f"✗ Import error: {e}")
        return False

    return True


def test_profile_loading():
    """Test that profiles can be loaded."""
    print("\nTesting profile loading...")

    try:
        from simulation.fake_profiles.profile_loader import ProfileLoader
        loader = ProfileLoader()
        profiles = loader.load_all_profiles()

        print(f"✓ Loaded {len(profiles)} profiles")

        for profile_id in profiles:
            print(f"  - {profile_id}")

    except Exception as e:
        print(f"✗ Profile loading error: {e}")
        return False

    return True


def test_api_key():
    """Test that API key can be loaded."""
    print("\nTesting API key loading...")

    try:
        import streamlit as st
        api_key = st.secrets["GEMINI_API_KEY"]
        print("✓ API key found in Streamlit secrets")
        return True
    except:
        try:
            import toml
            secrets_path = Path(".streamlit/secrets.toml")
            if secrets_path.exists():
                secrets = toml.load(secrets_path)
                if "GEMINI_API_KEY" in secrets:
                    print("✓ API key found in secrets.toml")
                    return True
        except:
            pass

    print("✗ No API key found")
    return False


def main():
    print("=" * 50)
    print("SIMULATION SETUP TEST")
    print("=" * 50)

    tests_passed = 0
    tests_total = 3

    if test_imports():
        tests_passed += 1

    if test_profile_loading():
        tests_passed += 1

    if test_api_key():
        tests_passed += 1

    print("\n" + "=" * 50)
    print(f"RESULTS: {tests_passed}/{tests_total} tests passed")

    if tests_passed == tests_total:
        print("✅ Setup is complete! You can run the experiment.")
        print("\nTo run:")
        print("  Test mode: python simulation/run_experiment.py --test")
        print("  Full mode: python simulation/run_experiment.py")
    else:
        print("❌ Setup incomplete. Please fix the errors above.")


if __name__ == "__main__":
    main()