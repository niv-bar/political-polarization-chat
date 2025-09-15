"""
Main script to run the conversation simulation experiment.
"""
import sys
import argparse
from pathlib import Path
import json
from datetime import datetime
import streamlit as st

# Add parent directory to path for imports
sys.path.append(str(Path(__file__).parent.parent))

from simulation.experiment_controller import ExperimentController


def get_api_key():
    """Get API key from Streamlit secrets or environment."""
    try:
        # Try to get from Streamlit secrets
        return st.secrets["GEMINI_API_KEY"]
    except:
        # If not in Streamlit context, try to load directly
        try:
            import toml
            secrets_path = Path(".streamlit/secrets.toml")
            if secrets_path.exists():
                secrets = toml.load(secrets_path)
                return secrets.get("GEMINI_API_KEY")
        except:
            pass

    return None


def main():
    """Main entry point for running the experiment."""

    parser = argparse.ArgumentParser(
        description="Run conversation simulation experiment"
    )

    parser.add_argument(
        "--test",
        action="store_true",
        help="Run in test mode (only 3 conversations)"
    )

    parser.add_argument(
        "--profiles",
        type=str,
        nargs="+",
        help="Specific profile IDs to use"
    )

    parser.add_argument(
        "--output-dir",
        type=str,
        default="simulation/results",
        help="Output directory for results"
    )

    parser.add_argument(
        "--api-key",
        type=str,
        required=False,
        help="Gemini API key (optional, will use secrets.toml if not provided)"
    )

    args = parser.parse_args()

    # Get API key
    api_key = args.api_key or get_api_key()

    if not api_key:
        print("❌ Error: No API key found!")
        print("Please either:")
        print("1. Add GEMINI_API_KEY to .streamlit/secrets.toml")
        print("2. Pass it with --api-key argument")
        sys.exit(1)

    print("\n" + "=" * 60)
    print("POLITICAL CONVERSATION SIMULATION EXPERIMENT")
    print("=" * 60)
    print(f"Start time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"Test mode: {args.test}")
    print(f"Output directory: {args.output_dir}")
    print(f"API key: {'Found in secrets' if not args.api_key else 'Provided'}")
    print("=" * 60 + "\n")

    # Initialize controller
    controller = ExperimentController(
        gemini_api_key=api_key,
        output_dir=args.output_dir
    )

    # Run experiment
    try:
        results = controller.run_experiment(
            test_mode=args.test,
            specific_profiles=args.profiles
        )

        # Check if successful
        if results['metadata']['total_successful'] > 0:
            print("\n✅ Experiment completed successfully!")

            # Validate balance
            balance = controller.validate_balance(results)
            print(f"\nBalance check: {'✓ Balanced' if balance['is_balanced'] else '✗ Unbalanced'}")

        else:
            print("\n❌ No successful conversations completed")

    except KeyboardInterrupt:
        print("\n\n⚠️  Experiment interrupted by user")
        sys.exit(1)

    except Exception as e:
        print(f"\n❌ Experiment failed: {str(e)}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()