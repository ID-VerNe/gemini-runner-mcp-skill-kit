# gemini-runner-mcp-skill-kit

[English README](./README.en.md)

面向自动化与 Agent 工作流的 **Gemini CLI 隔离执行套件**（机器优先输出、MCP 可调用、Skill 可复用）。

## 这个项目解决什么问题

当 Agent 直接运行 Gemini CLI 时，流式输出会污染主会话上下文。

`gemini_runner.py` 通过隔离子进程执行 Gemini，把完整日志写入 artifacts，并在 stdout 只输出一行机器可解析协议，方便上层工具稳定集成。

## 机器模式输出协议（默认）

```text
RESULT_JSON=C:\absolute\path\to\.gemini-runs\<run_id>\result.json
```

上层包装器应解析这行路径，再读取 `result.json`。

## 快速开始

在仓库根目录执行：

```bash
python gemini_runner.py run-audit --task "请审计当前仓库"
```

常用参数示例：

```bash
python gemini_runner.py run-audit ^
  --task "检查认证逻辑风险" ^
  --cwd "C:\path\to\repo" ^
  --mode default ^
  --timeout-seconds 120
```

续接会话：

```bash
python gemini_runner.py run-audit ^
  --task "基于上一轮继续分析并给修复建议" ^
  --resume-session "<session_id>"
```

## 运行模式

- `default`: 默认审批行为
- `auto_edit`: 映射为 `--approval-mode auto_edit`
- `yolo`: 映射为 `-y`
- `plan`: 映射为 `--approval-mode plan`

## 人类可读模式（仅调试）

```bash
python gemini_runner.py run-audit --task "..." --human-stream --human-render compact
```

仅用于手工排查，自动化场景请坚持机器模式。

## 产物目录

每次运行会生成 `.gemini-runs/<run_id>/`：

- `result.json`: 结构化最终结果（主读取目标）
- `events.jsonl`: 原始事件流
- `stdout.txt`: 聚合文本输出
- `stderr.txt`: Gemini CLI 错误输出
- `meta.json`: 运行元数据（args、cwd、return code 等）

## MCP 集成

使用 `mcp_server.py` 作为 stdio MCP server，暴露工具：

- `gemini_audit`

完整接入步骤见：

- `docs/MCP-INTEGRATION.md`

自动配置（Copilot CLI + Claude Desktop）：

```bash
python setup_mcp.py
```

配置示例文件：

- `config/mcp-config.example.json`

Skill 文件位置：

- `skills/SKILL.md`
- `docs/SKILL-USAGE.md`

## 测试与验证

运行全量测试：

```bash
python -m unittest discover -s tests -v
```

