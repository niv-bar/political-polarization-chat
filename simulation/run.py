# Test mode (3 conversations):
# python simulation/run_experiment.py --api-key YOUR_API_KEY --test

# Full experiment (30 conversations):
# python simulation/run_experiment.py --api-key YOUR_API_KEY

"""
How to Run

First, test your setup:
python simulation/test_setup.py

Run a test experiment (3 conversations):
python simulation/run_experiment.py --test
or
python simulation/run_experiment.py --test --profiles left_profile_1

Run the full experiment (30 conversations):
python simulation/run_experiment.py

"""

from simulation.metrics_analyzer import MetricsAnalyzer

analyzer = MetricsAnalyzer()
analyzer.generate_report(output_file="analysis_results.csv")