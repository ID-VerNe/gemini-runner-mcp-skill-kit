#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Comprehensive integration test for gemini-runner covering all scenarios.
"""
import json
import subprocess
import sys
import time
from pathlib import Path

# Force UTF-8 encoding for Windows console
if sys.platform == "win32":
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')

# Test results tracker
results = {
    "passed": [],
    "failed": [],
    "skipped": []
}

def run_test(name, command, expected_status="ok", check_fn=None):
    """Run a test and check results."""
    print(f"\n{'='*60}")
    print(f"TEST: {name}")
    print(f"{'='*60}")
    print(f"Command: {' '.join(command)}")
    
    try:
        result = subprocess.run(
            command,
            capture_output=True,
            text=True,
            timeout=180,  # 3 minutes max per test
            cwd=Path(__file__).parent.parent.parent.parent
        )
        
        print(f"Exit code: {result.returncode}")
        print(f"STDOUT:\n{result.stdout}")
        if result.stderr:
            print(f"STDERR:\n{result.stderr}")
        
        # Parse result.json path from stdout
        result_line = None
        for line in result.stdout.split("\n"):
            if line.strip().startswith("RESULT_JSON="):
                result_line = line.strip().replace("RESULT_JSON=", "")
                break
        
        if not result_line:
            print(f"❌ FAILED: No RESULT_JSON output")
            results["failed"].append(name)
            return None
        
        # Load and check result
        result_path = Path(result_line)
        if not result_path.exists():
            print(f"❌ FAILED: Result file not found: {result_path}")
            results["failed"].append(name)
            return None
        
        with open(result_path, "r", encoding="utf-8") as f:
            result_data = json.load(f)
        
        print(f"\nResult:")
        print(f"  Status: {result_data['status']}")
        print(f"  Session ID: {result_data['session_id']}")
        print(f"  Duration: {result_data['timing']['duration_ms']}ms")
        print(f"  Tool uses: {len(result_data['tool_uses'])}")
        print(f"  Errors: {len(result_data['errors'])}")
        
        # Check expected status
        if result_data['status'] != expected_status:
            print(f"❌ FAILED: Expected status '{expected_status}', got '{result_data['status']}'")
            results["failed"].append(name)
            return result_data
        
        # Run custom check function if provided
        if check_fn:
            if not check_fn(result_data):
                print(f"❌ FAILED: Custom check failed")
                results["failed"].append(name)
                return result_data
        
        print(f"✅ PASSED")
        results["passed"].append(name)
        return result_data
        
    except subprocess.TimeoutExpired:
        print(f"❌ FAILED: Timeout after 180s")
        results["failed"].append(name)
        return None
    except Exception as e:
        print(f"❌ FAILED: Exception: {e}")
        results["failed"].append(name)
        return None


def main():
    runner_path = Path(__file__).parent.parent / "gemini_runner.py"
    
    print("=" * 60)
    print("GEMINI RUNNER COMPREHENSIVE INTEGRATION TESTS")
    print("=" * 60)
    
    # Test 1: Basic task execution (default mode)
    result1 = run_test(
        "1. Basic task - default mode",
        [
            sys.executable, str(runner_path), "run-audit",
            "--task", "List the files in current directory",
            "--timeout-seconds", "120"  # Increased timeout
        ],
        expected_status="ok",
        check_fn=lambda r: r['session_id'] != ""
    )
    
    # Test 2: Resume session
    if result1 and result1.get('session_id'):
        session_id = result1['session_id']
        run_test(
            "2. Resume session",
            [
                sys.executable, str(runner_path), "run-audit",
                "--task", "Now count how many files were listed",
                "--resume-session", session_id,
                "--timeout-seconds", "120"  # Increased timeout
            ],
            expected_status="ok",
            check_fn=lambda r: r['session_id'] == session_id
        )
    else:
        print("\n⚠️  SKIPPED: Test 2 (Resume session) - no session from test 1")
        results["skipped"].append("2. Resume session")
    
    # Test 3: Auto-edit mode
    run_test(
        "3. Auto-edit mode",
        [
            sys.executable, str(runner_path), "run-audit",
            "--task", "What is 2+2?",
            "--mode", "auto_edit",
            "--timeout-seconds", "90"  # Increased timeout
        ],
        expected_status="ok"
    )
    
    # Test 4: Specific working directory
    run_test(
        "4. Specific working directory",
        [
            sys.executable, str(runner_path), "run-audit",
            "--task", "List files in current directory",
            "--cwd", str(Path(__file__).parent.parent),
            "--timeout-seconds", "120"  # Increased timeout
        ],
        expected_status="ok",
        check_fn=lambda r: len(r['tool_uses']) > 0
    )
    
    # Test 5: Timeout handling
    run_test(
        "5. Timeout handling",
        [
            sys.executable, str(runner_path), "run-audit",
            "--task", "Analyze the entire codebase in detail",
            "--timeout-seconds", "3"  # Very short timeout
        ],
        expected_status="timeout",
        check_fn=lambda r: any("timeout" in e for e in r['errors'])
    )
    
    # Test 6: Empty/quick response
    run_test(
        "6. Quick response",
        [
            sys.executable, str(runner_path), "run-audit",
            "--task", "Say hello",
            "--timeout-seconds", "90"  # Increased timeout
        ],
        expected_status="ok"
    )
    
    # Test 7: Tool usage verification
    run_test(
        "7. Tool usage verification",
        [
            sys.executable, str(runner_path), "run-audit",
            "--task", "Read the README.md file",
            "--timeout-seconds", "120"  # Increased timeout
        ],
        expected_status="ok",
        check_fn=lambda r: any(t['name'] == 'read_file' for t in r['tool_uses'])
    )
    
    # Print summary
    print("\n" + "=" * 60)
    print("TEST SUMMARY")
    print("=" * 60)
    print(f"✅ Passed: {len(results['passed'])}")
    for test in results['passed']:
        print(f"   - {test}")
    
    if results['failed']:
        print(f"\n❌ Failed: {len(results['failed'])}")
        for test in results['failed']:
            print(f"   - {test}")
    
    if results['skipped']:
        print(f"\n⚠️  Skipped: {len(results['skipped'])}")
        for test in results['skipped']:
            print(f"   - {test}")
    
    print("\n" + "=" * 60)
    total = len(results['passed']) + len(results['failed'])
    if total > 0:
        success_rate = (len(results['passed']) / total) * 100
        print(f"Success rate: {success_rate:.1f}%")
    
    # Return exit code
    return 0 if not results['failed'] else 1


if __name__ == "__main__":
    sys.exit(main())
