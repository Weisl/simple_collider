#!/usr/bin/env python3
"""Run every tests/test_*.py file inside headless Blender and report results.

Each test file already documents how to run itself individually::

    blender --background --python tests/test_bounding_sphere.py

This script just does that for every test file in this directory and
aggregates the results into a single pass/fail summary and exit code, so
the whole suite can be run with one command locally or in CI::

    python tests/run_tests.py --blender /path/to/blender
"""
import argparse
import subprocess
import sys
from pathlib import Path

TESTS_DIR = Path(__file__).resolve().parent


def discover_test_files():
    return sorted(TESTS_DIR.glob('test_*.py'))


def run_test_file(blender, test_file):
    result = subprocess.run(
        [
            blender,
            '--background',
            '--factory-startup',
            '--python', str(test_file),
            '--', '-v',
        ],
    )
    return result.returncode == 0


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        '--blender', default='blender',
        help="Path to the Blender executable to test against (default: "
             "'blender' on PATH).",
    )
    args = parser.parse_args()

    test_files = discover_test_files()
    if not test_files:
        print(f"No test_*.py files found in {TESTS_DIR}", file=sys.stderr)
        return 1

    results = []
    for test_file in test_files:
        print(f"\n=== Running {test_file.name} ===")
        passed = run_test_file(args.blender, test_file)
        results.append((test_file.name, passed))

    print("\n=== Summary ===")
    for name, passed in results:
        print(f"{'PASS' if passed else 'FAIL'}  {name}")

    failures = [name for name, passed in results if not passed]
    if failures:
        print(f"\n{len(failures)} of {len(results)} test file(s) failed.")
        return 1

    print(f"\nAll {len(results)} test file(s) passed.")
    return 0


if __name__ == '__main__':
    sys.exit(main())
