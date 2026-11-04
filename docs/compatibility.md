# skill-style-polish

> 让 AI 用**你自己的口吻**润色文字：从你电脑上所有 AI agent 的聊天记录里学你怎么说话。

**English:** One command (`python3 scripts/run.py`). An agent skill that mines *your own typed messages* from local AI-agent sessions (Claude Code, Codex, Cursor, pi, …), **fully automatically** separates human-typed messages from agent-generated prompts, detects and redacts sensitive entities (fail-closed), builds a Chinese-first style profile (spoken vs. written), polishes drafts in your voice, scores them, and keeps learning from your edits.



## 它做什么
1. **采集**：插件式适配器读取本地会话，只保留你亲手打的字（去掉工具输出、代码、大段粘贴）。
2. **自动去噪 + 隐私过滤**：自动区分人手打的消息和 agent 生成的提示；自动识别公司、项目、人名等敏感实体并脱敏，连同密码、token、手机号、邮箱、身份证、卡号、网址、金额，无需手填敏感词。
3. **建档**：中文特征——用词、句长、语气词、口头禅、中英混用、标点、不喜欢的说法；口语和书面语分开。
4. **润色 + 打分**：只理顺语句不改意思，`check.py` 用可度量指标打分。
5. **持续学习**：对比 AI 原稿和你改过的版本，把规则追加进档案。

## 支持的工具
| 工具 | 位置 | 状态 |
|---|---|---|
| Claude Code | `~/.claude/projects/*/*.jsonl` | ✅ 已实测（Linux + macOS） |
| Codex CLI / App | `~/.codex/sessions/**/rollout-*.jsonl`（`item_completed` → `UserMessage`） | ✅ 已实测（macOS） |
| pi | `~/.pi/agent/sessions/**/*.jsonl` | ✅ 已实测（macOS） |
| Cursor | `~/.cursor/projects/*/agent-transcripts/`、`workspaceStorage/*/state.vscdb`（aiService.prompts）、`globalStorage/state.vscdb` | ✅ 已实测（macOS；新版对话正文多在云端/加密，本地能取到的不多） |
| DeepSeek Harness | `~/.deepseek/sessions/*.json` | ✅ 已实测（macOS） |
| OpenCode | `~/.local/share/opencode/opencode.db` | ✅ 已实测（macOS） |
| DeepSeek 网页版 / ChatGPT 导出 / Gemini CLI | 导出的 JSON，`--adapter generic --path` | ⚠️ 通用解析，未用真实导出验证 |
| Google Antigravity | `~/.gemini/antigravity*/conversations/*.db` | ❌ 步骤是 protobuf 二进制，暂不支持 |
| 其他 | 让 agent 自己找文件、补适配器 | fallback |


## 安装
需要 Python 3.9+，只用标准库，不用装依赖。

```bash
# Claude Code
git clone https://github.com/bmdy6/skill-style-polish ~/.claude/skills/style-polish
# Codex / 其他支持 skills 的 agent（任选）
git clone https://github.com/bmdy6/skill-style-polish ~/.codex/skills/style-polish
git clone https://github.com/bmdy6/skill-style-polish ~/.agents/skills/style-polish
```

## 使用（一条命令，全自动）
```bash
cd ~/.claude/skills/style-polish
python3 scripts/run.py --no-llm          # 或不加 --no-llm，让 agent 审阅候选实体
```
它依次完成采集 → 去噪 → 自动识别敏感实体 → 脱敏 → 统计 → 生成档案 → 泄漏闸门。档案写到 `~/.style-polish/spoken.md`，在仓库之外，永远不会被提交。语料在 `./corpus/`，已被 git 忽略。

之后直接对 agent 说：
- "用我的口吻润色这段"
- "按我的文风检查这篇草稿"（`python3 scripts/check.py draft.txt --profile ~/.style-polish/spoken.md`）
- "这是我改过的版本，学一下"（见 `prompts/learn_from_edits.md`）

示例档案（合成数据，不是真实用户的）：[examples/spoken.example.md](../examples/spoken.example.md)

### 自动化细节
- **自动去噪**：子代理会话、非交互调用（sdk、`codex exec`）直接丢掉；其余消息按模板前缀重复、近似重复、结构化排版、回复太快、打字速度不像人、批量同时开会话、单消息会话、临时目录等信号打分。报告见 `corpus/denoise_report.json`，只有计数。
- **自动敏感实体**：从工作目录名、@提及、私有域名、GitHub owner、驼峰词、"XX公司/团队/老师"等结构里找候选词，再按出现在多少个会话里、是否在普通句子里也常用来打分。高分直接脱敏，中间分由 agent 只看词表决定，拿不准就脱敏（fail-closed）。结果写进可审计的 `corpus/auto_sensitive.json`（权限 0600）。
- **档案只存风格**：只存统计量和白名单词频，写盘前会自动消毒，再过 `check.py --leak-gate`。

设计和校准记录见 [docs/DESIGN.md](DESIGN.md)。

## 隐私
语料和档案只在本地，`.gitignore` 已排除 `corpus/`、`profiles/spoken.md`、`profiles/written.md`、`sensitive_words.txt`。

## License
MIT

---
Topics: `claude-skill` `ai-agent` `writing-style` `chinese`
