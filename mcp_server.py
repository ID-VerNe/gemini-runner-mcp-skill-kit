#!/usr/bin/env python3
"""
MCP Server for Gemini Runner - exposes isolated Gemini audit as a tool.

Usage:
    python mcp_server.py

MCP clients can then call the "gemini_audit" tool with task/cwd/model parameters.
"""
import asyncio
import json
import sys
from pathlib import Path
from typing import Any, Dict

# Add parent dir to path for gemini_runner import
sys.path.insert(0, str(Path(__file__).parent))
import gemini_runner


async def handle_list_tools() -> Dict[str, Any]:
    """Return available tools schema."""
    return {
        "tools": [
            {
                "name": "gemini_audit",
                "description": (
                    "Run an isolated Gemini CLI audit task with no context pollution. "
                    "Returns structured result with final_text, errors, and tool uses. "
                    "Perfect for code review, security audits, or data extraction tasks."
                ),
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "task": {
                            "type": "string",
                            "description": "The audit prompt/task to send to Gemini CLI"
                        },
                        "cwd": {
                            "type": "string",
                            "description": "Working directory for Gemini (default: current dir)",
                            "default": "."
                        },
                        "model": {
                            "type": "string",
                            "description": "Gemini model to use (default: use Gemini's default)",
                            "default": ""
                        },
                        "mode": {
                            "type": "string",
                            "enum": ["default", "auto_edit", "yolo", "plan"],
                            "description": "Approval mode (default: default)",
                            "default": "default"
                        },
                        "timeout_seconds": {
                            "type": "integer",
                            "description": "Task timeout in seconds (default: 1800)",
                            "default": 1800
                        },
                        "resume_session": {
                            "type": "string",
                            "description": "Optional: resume from previous session ID",
                            "default": ""
                        }
                    },
                    "required": ["task"]
                }
            }
        ]
    }


async def handle_call_tool(name: str, arguments: Dict[str, Any]) -> Dict[str, Any]:
    """Execute tool and return result."""
    if name != "gemini_audit":
        return {
            "content": [
                {
                    "type": "text",
                    "text": f"Unknown tool: {name}"
                }
            ],
            "isError": True
        }

    task = str(arguments.get("task", "")).strip()
    if not task:
        return {
            "content": [
                {
                    "type": "text",
                    "text": "Error: 'task' parameter is required"
                }
            ],
            "isError": True
        }
    if len(task) > 50000:
        return {
            "content": [
                {
                    "type": "text",
                    "text": "Error: 'task' parameter exceeds 50KB limit"
                }
            ],
            "isError": True
        }

    # Use caller's working directory by default
    # This is critical: Gemini CLI must run in the same directory as the agent
    # to see the same files and context
    import os
    cwd = str(arguments.get("cwd", "")).strip()
    if not cwd or cwd == ".":
        cwd = os.getcwd()  # Use the directory where MCP server was invoked from
    else:
        cwd_path = Path(cwd).resolve()
        if not cwd_path.exists():
            return {
                "content": [{"type": "text", "text": f"Error: directory not found: {cwd}"}],
                "isError": True,
            }
        if not cwd_path.is_dir():
            return {
                "content": [{"type": "text", "text": f"Error: path is not a directory: {cwd}"}],
                "isError": True,
            }
        cwd = str(cwd_path)

    cfg = gemini_runner.RunnerConfig(
        task=task,
        cwd=cwd,
        cmd="gemini",
        model=arguments.get("model", ""),
        mode=arguments.get("mode", "default"),
        timeout_seconds=max(1, int(arguments.get("timeout_seconds", 1800))),
        output_dir=".gemini-runs",
        machine=True,  # Always machine mode for MCP
        human_stream=False,
        human_render="compact",
        resume_session=arguments.get("resume_session", ""),
    )

    try:
        out = gemini_runner.run_task(cfg)
        result = out["result"]
        
        # Build structured response for MCP client
        response_text = f"""# Gemini Audit Result

**Status:** {result['status']}
**Session ID:** {result['session_id']}
**Duration:** {result['timing']['duration_ms']}ms

## Summary
{result['summary_text']}

## Full Response
{result['final_text']}

## Tool Uses ({len(result['tool_uses'])})
"""
        for i, tool in enumerate(result['tool_uses'], 1):
            response_text += f"\n{i}. **{tool['name']}** - {tool['status']}"
        
        if result['errors']:
            response_text += f"\n\n## Errors ({len(result['errors'])})\n"
            for err in result['errors']:
                response_text += f"- {err}\n"

        response_text += f"\n\n**Artifacts:** `{out['result_path']}`"

        is_error = result['status'] not in ('ok', 'empty')
        
        return {
            "content": [
                {
                    "type": "text",
                    "text": response_text
                }
            ],
            "isError": is_error
        }
    except Exception as e:
        return {
            "content": [
                {
                    "type": "text",
                    "text": f"Runner exception: {e}"
                }
            ],
            "isError": True
        }


async def main():
    """MCP stdio server main loop."""
    loop = asyncio.get_event_loop()
    
    # Read stdin in a non-blocking way
    while True:
        try:
            line = await loop.run_in_executor(None, sys.stdin.readline)
            if not line:
                break
                
            line = line.strip()
            if not line:
                continue
                
            msg = json.loads(line)
            if not isinstance(msg, dict):
                continue
        except json.JSONDecodeError as e:
            print(f"Invalid JSON input: {e}", file=sys.stderr)
            continue
        except Exception as e:
            print(f"Fatal MCP loop error: {e}", file=sys.stderr)
            break

        msg_id = msg.get("id")
        method = msg.get("method", "")

        if method == "initialize":
            response = {
                "jsonrpc": "2.0",
                "id": msg_id,
                "result": {
                    "protocolVersion": "2024-11-05",
                    "capabilities": {
                        "tools": {}
                    },
                    "serverInfo": {
                        "name": "gemini-runner-mcp",
                        "version": "1.0.0"
                    }
                }
            }
        elif method == "tools/list":
            result = await handle_list_tools()
            response = {
                "jsonrpc": "2.0",
                "id": msg_id,
                "result": result
            }
        elif method == "tools/call":
            params = msg.get("params", {})
            tool_name = params.get("name", "")
            tool_args = params.get("arguments", {})
            result = await handle_call_tool(tool_name, tool_args)
            response = {
                "jsonrpc": "2.0",
                "id": msg_id,
                "result": result
            }
        else:
            response = {
                "jsonrpc": "2.0",
                "id": msg_id,
                "error": {
                    "code": -32601,
                    "message": f"Method not found: {method}"
                }
            }

        print(json.dumps(response), flush=True)


if __name__ == "__main__":
    asyncio.run(main())
