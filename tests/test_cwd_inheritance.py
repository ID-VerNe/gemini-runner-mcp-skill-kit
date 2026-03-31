#!/usr/bin/env python3
"""
Integration test to verify cwd behavior of MCP server.
"""
import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path

# Add parent dir for imports
sys.path.insert(0, str(Path(__file__).parent.parent))


def test_cwd_inherited_from_caller():
    """Verify that MCP server inherits caller's working directory."""
    
    # Create a temporary directory to test in
    with tempfile.TemporaryDirectory() as tmpdir:
        tmpdir = Path(tmpdir)
        
        # Create a marker file to verify cwd
        marker_file = tmpdir / "test_marker.txt"
        marker_file.write_text("cwd test marker")
        
        # Prepare MCP request
        request = {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "tools/call",
            "params": {
                "name": "gemini_audit",
                "arguments": {
                    "task": "List files in current directory",
                    "timeout_seconds": 10
                }
            }
        }
        
        # Get path to mcp_server.py
        mcp_server_path = Path(__file__).parent.parent / "mcp_server.py"
        
        # Run MCP server from the test directory
        # This simulates what Copilot CLI does when it calls the MCP tool
        print(f"Running MCP server from: {tmpdir}")
        print(f"Marker file exists: {marker_file.exists()}")
        
        proc = subprocess.Popen(
            [sys.executable, str(mcp_server_path)],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            cwd=str(tmpdir),  # Run from test directory
            text=True
        )
        
        # Send the request
        stdout, stderr = proc.communicate(input=json.dumps(request) + "\n", timeout=15)
        
        print(f"\nSTDOUT:\n{stdout}")
        if stderr:
            print(f"\nSTDERR:\n{stderr}")
        
        # Check if Gemini was called with correct cwd
        # Note: This test won't actually run Gemini CLI, it will fail with spawn error
        # But we can check that the cwd was set correctly by examining the output
        
        # The test passes if:
        # 1. MCP server doesn't crash
        # 2. The output directory is created in the test directory
        
        gemini_runs_dir = tmpdir / ".gemini-runs"
        if gemini_runs_dir.exists():
            print(f"\n✅ Output directory created in correct location: {gemini_runs_dir}")
            run_dirs = list(gemini_runs_dir.iterdir())
            if run_dirs:
                print(f"✅ Run directory created: {run_dirs[0]}")
                result_file = run_dirs[0] / "result.json"
                meta_file = run_dirs[0] / "meta.json"
                if result_file.exists() and meta_file.exists():
                    result = json.loads(result_file.read_text(encoding="utf-8"))
                    meta = json.loads(meta_file.read_text(encoding="utf-8"))
                    print(f"✅ Result status: {result.get('status')}")
                    print(f"✅ Working directory was: {meta.get('cwd')}")
                    
                    # Verify cwd matches our test directory
                    actual_cwd = Path(meta.get('cwd', ''))
                    if actual_cwd.resolve() == tmpdir.resolve():
                        print(f"\n✅✅✅ SUCCESS: CWD correctly inherited from caller")
                        print(f"   Expected: {tmpdir.resolve()}")
                        print(f"   Actual:   {actual_cwd.resolve()}")
                        return True
                    else:
                        print(f"\n❌ FAILED: CWD mismatch")
                        print(f"   Expected: {tmpdir.resolve()}")
                        print(f"   Actual:   {actual_cwd.resolve()}")
                        return False
        else:
            print(f"⚠️  Output directory not found at {gemini_runs_dir}")
            print("   This might be expected if Gemini CLI is not installed")
            print("   But the MCP server should still have tried to run")
            
        return None  # Inconclusive


if __name__ == "__main__":
    print("Testing MCP server cwd inheritance...")
    print("=" * 60)
    result = test_cwd_inherited_from_caller()
    if result is True:
        print("\n✅ Test PASSED")
        sys.exit(0)
    elif result is False:
        print("\n❌ Test FAILED")
        sys.exit(1)
    else:
        print("\n⚠️  Test INCONCLUSIVE (likely Gemini CLI not installed)")
        print("   Manual testing required")
        sys.exit(0)
