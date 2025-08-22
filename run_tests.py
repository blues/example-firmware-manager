#!/usr/bin/env python3
"""
Test runner script for the auth module tests.

This script runs all unit tests and optionally collects coverage data.
Usage:
    python run_tests.py          # Run tests without coverage
    python run_tests.py --coverage   # Run tests with coverage report
"""

import sys
import os
import unittest
import argparse
from pathlib import Path


def install_coverage_if_needed():
    """Install coverage package if it's not available and coverage is requested."""
    try:
        import coverage
        return True
    except ImportError:
        print("Coverage package not found. Installing...")
        import subprocess
        try:
            subprocess.check_call([sys.executable, "-m", "pip", "install", "coverage"])
            import coverage
            return True
        except subprocess.CalledProcessError:
            print("ERROR: Failed to install coverage package.")
            print("Please install it manually: pip install coverage")
            return False


def run_tests_with_coverage():
    """Run tests with coverage collection."""
    if not install_coverage_if_needed():
        return False
    
    import coverage
    
    # Start coverage collection
    cov = coverage.Coverage(
        source=['auth', 'rules_engine', 'manage_firmware'],
        omit=[
            '*/tests/*',
            '*/test_*',
            'run_tests.py'
        ]
    )
    cov.start()
    
    # Run the tests
    loader = unittest.TestLoader()
    start_dir = os.path.join(os.path.dirname(__file__), 'tests')
    suite = loader.discover(start_dir, pattern='test_*.py')
    
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    
    # Stop coverage and generate report
    cov.stop()
    cov.save()
    
    print("\n" + "="*50)
    print("COVERAGE REPORT")
    print("="*50)
    
    # Generate console report
    cov.report(show_missing=True)
    
    # Generate HTML report if possible
    try:
        html_dir = os.path.join(os.path.dirname(__file__), 'htmlcov')
        cov.html_report(directory=html_dir)
        print(f"\nHTML coverage report generated in: {html_dir}/index.html")
    except Exception as e:
        print(f"Could not generate HTML report: {e}")
    
    return result.wasSuccessful()


def run_tests_without_coverage():
    """Run tests without coverage collection."""
    loader = unittest.TestLoader()
    start_dir = os.path.join(os.path.dirname(__file__), 'tests')
    suite = loader.discover(start_dir, pattern='test_*.py')
    
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    
    return result.wasSuccessful()


def main():
    """Main function to parse arguments and run tests."""
    parser = argparse.ArgumentParser(description='Run unit tests for auth module')
    parser.add_argument(
        '--coverage', 
        action='store_true', 
        help='Run tests with coverage collection and reporting'
    )
    parser.add_argument(
        '--verbose', '-v',
        action='store_true',
        help='Verbose output (equivalent to unittest -v)'
    )
    
    args = parser.parse_args()
    
    # Change to the script's directory to ensure proper imports
    script_dir = os.path.dirname(os.path.abspath(__file__))
    os.chdir(script_dir)
    
    # Add current directory to Python path
    if script_dir not in sys.path:
        sys.path.insert(0, script_dir)
    
    print("Running auth module tests...")
    print("="*50)
    
    if args.coverage:
        success = run_tests_with_coverage()
    else:
        success = run_tests_without_coverage()
    
    if success:
        print("\n✅ All tests passed!")
        sys.exit(0)
    else:
        print("\n❌ Some tests failed!")
        sys.exit(1)


if __name__ == '__main__':
    main()