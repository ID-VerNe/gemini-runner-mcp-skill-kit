# Gemini Runner Team Onboarding

This guide helps your team start using `tools/gemini-runner` quickly and consistently.

## 1) What this component is

`gemini-runner` is an isolated execution layer around Gemini CLI:

- keeps parent agent context clean
- returns structured output for automation
- supports MCP tool access (`gemini_audit`)
- supports multi-turn sessions (`resume_session`)

## 2) Who should use what

- Engineers who want direct CLI usage: `gemini_runner.py`
- Agent users (Copilot/Claude): `mcp_server.py` + MCP config
- Team leads/reviewers: use for repeatable security/code audits

## 3) One-time setup

From repo root:

```bash
python tools\gemini-runner\setup_mcp.py
```

This configures:

- Copilot CLI: `~/.copilot/mcp-config.json`
- Claude Desktop: `%APPDATA%\Claude\claude_desktop_config.json` (Windows)

Then restart your client session.

## 4) Daily usage patterns

### A. Direct CLI (machine mode)

```bash
python tools\gemini-runner\gemini_runner.py run-audit --task "Audit auth flow"
```

stdout contract:

```text
RESULT_JSON=<absolute path to result.json>
```

### B. MCP tool usage (recommended for agents)

Ask your agent:

`Please use gemini_audit to run a security audit on this repository.`

### C. Continue a previous Gemini session

Use prior `session_id`:

```bash
python tools\gemini-runner\gemini_runner.py run-audit ^
  --task "Continue and propose patch plan" ^
  --resume-session "<session_id>"
```

## 5) Team conventions (recommended)

- Default `cwd`: repository root
- Default timeout:
  - quick checks: 120-300s
  - full audit: 1800s
- Always capture and store `result.json` path in issue/PR notes
- For follow-up analysis, reuse `session_id`

## 6) Outputs your team should read

Per run directory `.gemini-runs/<run_id>/`:

- `result.json` (source of truth)
- `events.jsonl` (debug timeline)
- `stderr.txt` (CLI diagnostics)
- `meta.json` (execution metadata)

## 7) Troubleshooting

- Tool missing in client:
  - rerun `setup_mcp.py`
  - restart client session
- Timeout:
  - increase `timeout_seconds`
  - narrow task scope
- CWD mismatch:
  - pass explicit `cwd`
- Empty/error status:
  - check `stderr.txt` and `events.jsonl`

## 8) Validation checklist before team rollout

Run:

```bash
cd tools\gemini-runner
python -m unittest discover -s tests -v
```

Expected: all tests pass.

## 9) Security and operational notes

- `task` has size limits in MCP path
- invalid `cwd` is rejected early
- config writes are atomic with backup on invalid existing JSON
- timeouts and process cleanup are handled to avoid leaks

## 10) Suggested rollout plan

1. Pilot with one repo and one team
2. Capture 5-10 audit runs and tune prompt templates
3. Standardize templates for security/bug/doc audits
4. Expand to all repos

