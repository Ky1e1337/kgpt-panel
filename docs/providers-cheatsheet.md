# Codewhale 多模型速查表（KGPT & Qwen）

两个自定义 provider，都指向中转站 `https://api.b.ai/v1`。

## Provider 概览

- **KGPT** — 模型 `glm-5.3-flash`，后端 GLM（Z.ai / 智谱）
- **Qwen** — 模型 `qwen3.8-flash`，后端通义千问（阿里）

## 单次调用（对话 / 任务）

- `codewhale --provider KGPT exec "你的任务描述"`
- `codewhale --provider Qwen exec "你的任务描述"`
- 需要工具（读写文件、跑命令、改代码）：加 `--auto`
  - `codewhale --provider KGPT exec --auto "修复 src 下的这个 bug"`
  - `codewhale --provider Qwen exec --auto "列出当前目录并说明"`
- 临时指定其他模型：加 `--model`
  - `codewhale --provider Qwen --model qwen3.8-max exec "..."`
  - `codewhale --provider KGPT --model glm-5.3 exec "..."` （glm-5.3 是 premium，需充值）

## 派发子 agent（fleet 批量）

- 初始化账本：`codewhale --provider KGPT fleet init`
- 批量派发：`codewhale --provider KGPT fleet run tasks.json --max-workers 4`
- 查看状态：`codewhale --provider KGPT fleet status`
- 换 Qwen 同理：把 `--provider KGPT` 换成 `--provider Qwen`

`tasks.json` 任务规格示例（JSON/TOML 均可）：

```json
[
  { "prompt": "任务 1 的完整描述" },
  { "prompt": "任务 2 的完整描述" }
]
```

## 改默认模型

编辑 `~/.codewhale/config.toml`，改对应表的 `model` 字段：

```toml
[providers.KGPT]
base_url = "https://api.b.ai/v1"
api_key  = "sk-…"
model    = "glm-5.3-flash"

[providers.Qwen]
base_url = "https://api.b.ai/v1"
api_key  = "sk-…"
model    = "qwen3.8-flash"
```

## 中转站可用模型（部分）

- GLM：`glm-5.1`、`glm-5.2`、`glm-5.3`、`glm-5.3-flash`
- Qwen：`qwen3.8-flash`、`qwen3.8-max`、`qwen3.8-27b`
- GPT：`gpt-5.2`、`gpt-5.4`、`gpt-5.5`、`gpt-5.6-*` 等
- Claude：`claude-opus-*`、`claude-sonnet-*`、`claude-haiku-4.5`
- Gemini：`gemini-3.1-pro`、`gemini-3-flash` 等
- 其他：`kimi-k2.6`、`kimi-k3`、`deepseek-v4-pro`、`deepseek-v4-flash`、`minimax-m3`、`hy3` 等

## 注意

- `glm-5.3` 被中转站标记为 premium，余额不足会返回 `Deposit required`，需充值后才能用。
- 两个 API key 都明文存在 `~/.codewhale/config.toml`，注意保密；介意的话到中转站后台轮换。
