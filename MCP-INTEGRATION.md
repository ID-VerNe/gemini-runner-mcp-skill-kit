# MCP Integration Guide for Gemini Runner

## What is this?

This MCP server exposes the `gemini_runner.py` tool as a **Model Context Protocol** tool that any MCP-compatible agent (Claude Desktop, GitHub Copilot CLI, etc.) can call programmatically.

## Why MCP over Skill?

**MCP** is better suited for this use case because:

- **Structured I/O**: MCP enforces strict JSON schema for inputs/outputs, reducing parsing errors.
- **Machine-first**: Default behavior is silent automation, no stdout pollution.
- **Composable**: MCP tools can be chained and orchestrated easily.
- **Error signaling**: Proper `isError` flag and typed responses.

**Skill** is better for:

- Human-interactive slash commands in chat apps.
- Quick ad-hoc tasks with natural language parsing.

For an isolated audit runner consumed by other agents, MCP is the correct choice.

## Quick Setup (Automatic)

Run the setup script to automatically configure both Claude Desktop and Copilot CLI:

```bash
python tools/gemini-runner/setup_mcp.py
```

This will add the `gemini-runner` MCP server to:
- **Claude Desktop**: `%APPDATA%\Claude\claude_desktop_config.json` (Windows)
- **Copilot CLI**: `~/.copilot/mcp-config.json`

Then restart the respective application.

## Manual Setup

### Claude Desktop

1. Locate your Claude Desktop MCP config file:
   - **Windows**: `%APPDATA%\Claude\claude_desktop_config.json`
   - **macOS**: `~/Library/Application Support/Claude/claude_desktop_config.json`
   - **Linux**: `~/.config/Claude/claude_desktop_config.json`

2. Add the `gemini-runner` server config:

```json
{
  "mcpServers": {
    "gemini-runner": {
      "command": "python",
      "args": [
        "C:\\absolute\\path\\to\\cc-connect\\tools\\gemini-runner\\mcp_server.py"
      ]
    }
  }
}
```

3. Restart Claude Desktop.

### GitHub Copilot CLI

1. Create or edit `~/.copilot/mcp-config.json`:

```json
{
  "mcpServers": {
    "gemini-runner": {
      "command": "python",
      "args": [
        "C:\\absolute\\path\\to\\cc-connect\\tools\\gemini-runner\\mcp_server.py"
      ],
      "description": "Isolated Gemini CLI runner for audits with no context pollution"
    }
  }
}
```

2. Restart your Copilot CLI session or start a new one.

3. The `gemini_audit` tool should now be available automatically.

## Verification

### For Claude Desktop
Check the Claude Desktop UI - the tool should appear in the available tools list.

### For Copilot CLI
The tool will be automatically available in your session. You can verify by asking:
```
What tools do you have access to?
```

Or directly use it:
```
Please use gemini_audit to analyze this repository
```

## Usage from Agent

Once configured, you can invoke it like:

```
Please use the gemini_audit tool to run a security audit on this repository.
```

The agent will call:

```json
{
  "name": "gemini_audit",
  "arguments": {
    "task": "Run a comprehensive security audit on this codebase and output findings in JSON format",
    "cwd": "/path/to/repo",
    "mode": "default"
  }
}
```

The tool returns structured markdown with:
- Status
- Session ID
- Summary
- Full response text
- Tool uses
- Errors (if any)
- Artifact path for detailed logs

## Advanced Options

```json
{
  "task": "Audit for SQL injection vulnerabilities",
  "cwd": ".",
  "model": "gemini-2.5-pro",
  "mode": "auto_edit",
  "timeout_seconds": 3600,
  "resume_session": "gemini-session-abc123"
}
```

## Troubleshooting

- **Tool not appearing**: Check Claude Desktop logs, ensure Python path is correct.
- **Timeout errors**: Increase `timeout_seconds` for large repositories.
- **Spawn errors**: Verify `gemini` CLI is in PATH and working.
- **Result not returned**: Check `.gemini-runs/<run_id>/` for full logs and stderr.

## Output Contract

The MCP tool always returns:
- `content[0].text`: Human-readable markdown summary
- `isError`: Boolean flag for success/failure
- Artifact reference for programmatic parsing

For automated consumption, parse the artifact JSON file referenced in the response.
