# gemini-runner

Machine-first isolated Gemini CLI runner for automation, MCP tools, and agent workflows.

## What this solves

When an agent directly runs Gemini CLI, raw stream output can pollute the parent session context.

`gemini_runner.py` runs Gemini in an isolated subprocess, writes full artifacts to disk, and prints a single machine-readable line to stdout.

## Output contract (machine mode, default)

```text
RESULT_JSON=C:\absolute\path\to\.gemini-runs\<run_id>\result.json
```

Wrappers should parse this line and read `result.json`.

## Quick start

From repository root:

```bash
python tools\gemini-runner\gemini_runner.py run-audit --task "Audit this repository"
```

Common options:

```bash
python tools\gemini-runner\gemini_runner.py run-audit ^
  --task "Find auth bugs" ^
  --cwd "C:\path\to\repo" ^
  --mode default ^
  --timeout-seconds 120
```

Resume a previous Gemini session:

```bash
python tools\gemini-runner\gemini_runner.py run-audit ^
  --task "Continue previous analysis and summarize fixes" ^
  --resume-session "<session_id>"
```

## Modes

- `default`: normal approval behavior
- `auto_edit`: maps to `--approval-mode auto_edit`
- `yolo`: maps to `-y`
- `plan`: maps to `--approval-mode plan`

## Human mode (debug only)

```bash
python tools\gemini-runner\gemini_runner.py run-audit --task "..." --human-stream --human-render compact
```

Use this only for manual debugging, not automation.

## Artifacts

Each run creates `.gemini-runs/<run_id>/`:

- `result.json`: structured final result
- `events.jsonl`: raw parsed stream-json events
- `stdout.txt`: aggregated assistant text
- `stderr.txt`: Gemini stderr
- `meta.json`: run metadata (args, cwd, return code, etc.)

## MCP integration

Use `mcp_server.py` as stdio MCP server.

Tool exposed: `gemini_audit`

See full setup in `MCP-INTEGRATION.md`.

Automatic setup for Copilot CLI + Claude Desktop:

```bash
python tools\gemini-runner\setup_mcp.py
```

## Validation status

Current automated tests cover:

- argument building and parsing safety
- spawn/timeout/error behavior
- MCP tool input validation (task size, cwd validity, unknown tool)
- setup script behavior (new config, invalid JSON backup, atomic write)

Run all tests:

```bash
cd tools\gemini-runner
python -m unittest discover -s tests -v
```

