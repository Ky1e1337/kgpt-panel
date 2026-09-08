# KGPT Panel — 子 agent 调度体系

本地子 agent 管理面板 + 多 agent 编排方法，用于派发 KGPT / Qwen 子 agent，并在浏览器里实时查看它们的思考过程。主 agent 可通过 HTTP API 主动调度，用户在前端「只看不背指令」。

## 组成

- **KGPT Panel**（`app.py` + `index.html`）：本地 web 面板，派发 / 监控 / 回复子 agent
- **`docs/多Agent编排速查表.md`**：多 agent 编排方法（delegate / best-of-n / dynamic-workflows 六模式、派 vs 留原则、四条铁律）
- **`docs/providers-cheatsheet.md`**：KGPT / Qwen provider 用法速查（含 fleet 派发、中转站模型列表）

## 快速开始

```bash
cd ~/kgpt-panel
python3 app.py
# 浏览器打开 http://127.0.0.1:8787
```

## 核心机制

- 后端调用 `codewhale --provider X exec --auto --output-format stream-json`
- 子 agent 自动继承主 agent 的完整能力：bash / read / edit / write / tool_search + 79 个 skill + MCP Registry（5201 个可安装服务器）
- 前端只显示文字（思考 + 回答），工具调用只留 `🔧` 标记，命令 / 输出 / JSON 全省略
- 「回复」通过 `codewhale --resume <session_id>` 带记忆续接同一会话
- 主 agent 调度时直接调面板 API，任务卡片自动跳出（前端 0.7s 轮询）

## 派发 API

| 方法 | 路径 | 说明 |
|------|------|------|
| POST | `/api/run` | 派发任务，body `{provider, prompt}` |
| POST | `/api/reply/<id>` | 带记忆回复，body `{message}` |
| POST | `/api/stop/<id>` | 终止任务（进程组 kill） |
| GET | `/api/tasks` | 任务列表 + 流式事件 |

## 依赖与前置

- Python 3（纯标准库，零 pip 依赖）
- `codewhale` CLI
- KGPT / Qwen provider 配置（见 `docs/providers-cheatsheet.md`；关键：`[providers.X]` 必须设 `kind = "openai-compatible"`，否则 `--auto` 工具模式报错）

## 已知限制

- codewhale `exec` 子 agent 不输出独立的 reasoning（隐藏思考链），前端显示的是模型的可见文字输出（content）
- 服务器进程需在终端前台运行（`python3 app.py`）；任务存内存，重启面板后历史清空
