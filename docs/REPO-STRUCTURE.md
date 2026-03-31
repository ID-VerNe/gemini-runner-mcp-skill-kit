# Repository Structure

This repository uses a normalized layout:

- `gemini_runner.py` — core isolated Gemini runner
- `mcp_server.py` — MCP stdio server exposing `gemini_audit`
- `setup_mcp.py` — automatic MCP config writer (Copilot CLI + Claude Desktop)
- `tests/` — unit and integration tests
- `docs/` — user/team/ops documentation
- `skills/` — skill prompt definitions (`SKILL.md`)
- `config/` — sample config files (`mcp-config.example.json`)

## Why this layout

- Keep executable entrypoints at root for simple usage
- Separate docs from runtime code
- Separate skill definitions from docs
- Keep config examples discoverable without mixing with generated state

