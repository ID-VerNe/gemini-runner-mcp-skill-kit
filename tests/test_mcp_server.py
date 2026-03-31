#!/usr/bin/env python3
"""
Tests for MCP server functionality.
"""
import json
import sys
import unittest
from pathlib import Path
from unittest.mock import patch

# Add parent dir for imports
sys.path.insert(0, str(Path(__file__).parent.parent))
import mcp_server


class TestMCPServer(unittest.TestCase):
    """Test MCP server request handling."""

    def test_list_tools_schema(self):
        """Verify tools/list returns correct schema."""
        import asyncio
        result = asyncio.run(mcp_server.handle_list_tools())
        
        self.assertIn("tools", result)
        self.assertEqual(len(result["tools"]), 1)
        
        tool = result["tools"][0]
        self.assertEqual(tool["name"], "gemini_audit")
        self.assertIn("description", tool)
        self.assertIn("inputSchema", tool)
        
        schema = tool["inputSchema"]
        self.assertEqual(schema["type"], "object")
        self.assertIn("task", schema["properties"])
        self.assertEqual(schema["required"], ["task"])

    def test_call_tool_missing_task(self):
        """Verify error when task parameter is missing."""
        import asyncio
        result = asyncio.run(mcp_server.handle_call_tool("gemini_audit", {}))
        
        self.assertTrue(result["isError"])
        self.assertIn("required", result["content"][0]["text"].lower())

    def test_call_tool_too_large_task(self):
        """Verify error when task parameter is too large."""
        import asyncio
        large_task = "x" * 50001
        result = asyncio.run(mcp_server.handle_call_tool("gemini_audit", {"task": large_task}))
        self.assertTrue(result["isError"])
        self.assertIn("50kb", result["content"][0]["text"].lower())

    def test_call_tool_invalid_cwd(self):
        """Verify error when cwd does not exist."""
        import asyncio
        result = asyncio.run(
            mcp_server.handle_call_tool("gemini_audit", {"task": "test", "cwd": "Z:\\this\\path\\does\\not\\exist"})
        )
        self.assertTrue(result["isError"])
        self.assertIn("directory not found", result["content"][0]["text"].lower())

    def test_call_tool_unknown_tool(self):
        """Verify error when tool name is unknown."""
        import asyncio
        result = asyncio.run(mcp_server.handle_call_tool("unknown_tool", {"task": "test"}))
        
        self.assertTrue(result["isError"])
        self.assertIn("Unknown tool", result["content"][0]["text"])

    @patch('gemini_runner.run_task')
    def test_call_tool_success(self, mock_run):
        """Verify successful tool call returns structured response."""
        import asyncio
        
        # Mock successful run
        mock_run.return_value = {
            "result_path": "/tmp/test/result.json",
            "result": {
                "status": "ok",
                "session_id": "test-session",
                "timing": {"duration_ms": 1234},
                "summary_text": "Test summary",
                "final_text": "Final response",
                "tool_uses": [
                    {"name": "bash", "status": "success"}
                ],
                "errors": []
            }
        }
        
        result = asyncio.run(mcp_server.handle_call_tool(
            "gemini_audit",
            {"task": "test audit task", "cwd": "."}
        ))
        
        self.assertFalse(result["isError"])
        self.assertIn("content", result)
        text = result["content"][0]["text"]
        self.assertIn("test-session", text)
        self.assertIn("ok", text)
        self.assertIn("bash", text)

    @patch('gemini_runner.run_task')
    def test_call_tool_with_errors(self, mock_run):
        """Verify tool call with errors sets isError flag."""
        import asyncio
        
        mock_run.return_value = {
            "result_path": "/tmp/test/result.json",
            "result": {
                "status": "error",
                "session_id": "test-session",
                "timing": {"duration_ms": 100},
                "summary_text": "Error occurred",
                "final_text": "",
                "tool_uses": [],
                "errors": ["spawn failed"]
            }
        }
        
        result = asyncio.run(mcp_server.handle_call_tool(
            "gemini_audit",
            {"task": "test"}
        ))
        
        self.assertTrue(result["isError"])
        text = result["content"][0]["text"]
        self.assertIn("spawn failed", text)

    @patch('gemini_runner.run_task')
    def test_call_tool_exception(self, mock_run):
        """Verify exception handling in tool call."""
        import asyncio
        
        mock_run.side_effect = RuntimeError("Test exception")
        
        result = asyncio.run(mcp_server.handle_call_tool(
            "gemini_audit",
            {"task": "test"}
        ))
        
        self.assertTrue(result["isError"])
        self.assertIn("exception", result["content"][0]["text"].lower())


if __name__ == "__main__":
    unittest.main()
