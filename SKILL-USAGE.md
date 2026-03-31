# Skill Version Guide (for Agents)

This folder includes a skill-style prompt file: `SKILL.md`.

Use it when your agent framework supports local skills (for example, scanning a `SKILL.md` and following its instructions to call tools).

## What this skill does

It standardizes how an agent should call the local MCP tool `gemini_audit`:

- safe defaults for `cwd`
- sensible timeout policy
- session resume workflow
- structured error and artifact handling

## Expected runtime dependency

The MCP server must already be configured:

- Copilot CLI: `~/.copilot/mcp-config.json`
- Claude Desktop: `%APPDATA%\Claude\claude_desktop_config.json`

and point to:

`tools\gemini-runner\mcp_server.py`

## Suggested invocation pattern

1. Ask agent to use the skill.
2. Skill instructs tool call:
   - `gemini_audit(task=..., cwd=..., timeout_seconds=...)`
3. Agent returns summary + status + artifact path.
4. For follow-up, pass prior `session_id` as `resume_session`.

## Example

Initial:

`Use gemini-runner-audit skill to audit this repository for auth vulnerabilities.`

Follow-up:

`Continue using previous Gemini session and propose patch plan.`

