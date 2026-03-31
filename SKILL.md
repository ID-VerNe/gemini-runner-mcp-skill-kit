---
name: gemini-runner-audit
description: Use isolated Gemini CLI audit via local MCP tool (`gemini_audit`) for context-safe code/security/doc analysis with optional session resume.
---

# Gemini Runner Audit Skill

Use this skill when you need Gemini to run in an isolated subprocess and return structured results without polluting the main agent context.

## When to use

- Deep code audit (security, correctness, architecture)
- Large repo analysis where clean parent context is important
- Multi-turn Gemini analysis using `resume_session`

## Tool to call

- MCP tool name: `gemini_audit`
- Required argument: `task`
- Optional arguments:
  - `cwd` (defaults to current working directory)
  - `model`
  - `mode`: `default | auto_edit | yolo | plan`
  - `timeout_seconds`
  - `resume_session`

## Default execution policy

1. Set `cwd` to current repo root unless user explicitly requests another path.
2. Start with `mode=default` and `timeout_seconds=1800` for heavy audits.
3. For short checks, use 120-300 seconds.
4. If the response includes a `Session ID`, reuse it for follow-up questions.

## Recommended prompts

- Security:
  - `Run a comprehensive security audit of this repository and rank findings by severity.`
- Bug hunt:
  - `Find concrete logic bugs and race conditions with file/line references.`
- Docs quality:
  - `Evaluate README and docs for gaps, inconsistencies, and missing operational steps.`

## Output handling

Always parse and surface:

- `Status`
- `Session ID`
- `Summary` / `Full Response`
- `Tool Uses`
- `Errors`
- `Artifacts` path (`result.json`)

If status is `error` or `timeout`, include clear next action:

- increase timeout
- narrow task scope
- retry with same `resume_session` if applicable

## Guardrails

- Do not stream human mode for automation.
- Do not suppress Gemini errors; report them explicitly.
- Keep filesystem scope aligned with `cwd` to match user-visible project context.

