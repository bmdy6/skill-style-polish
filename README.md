# skill-style-polish

> 让 AI 用**你自己的口吻**润色文字：从你电脑上所有 AI agent 的聊天记录里学你怎么说话。

**English:** An agent skill that mines *your own typed messages* from local AI-agent sessions (Claude Code, Codex, Cursor, pi, …), strips secrets/PII, builds a Chinese-first style profile (spoken vs. written), polishes drafts in your voice, scores them, and keeps learning from your edits.

![demo](docs/assets/demo.gif)
<!-- TODO: 放截图或演示 GIF -->

## 它做什么
1. **采集**：插件式适配器读取本地会话，只保留你亲手打的字（去掉工具输出、代码、大段粘贴）。
2. **隐私过滤**：脱敏密码、token、手机号、邮箱、身份证、卡号；自定义敏感词表命中整条丢弃。
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
```bash
git clone https://github.com/bmdy6/skill-style-polish ~/.claude/skills/style-polish
```
只依赖 Python 3 标准库。

## 使用（全自动）
```bash
cd ~/.claude/skills/style-polish
python3 scripts/run.py      # 采集 → 去噪 → 自动识别敏感实体 → 脱敏 → 统计
```
然后对 agent 说："按我的文风建档" / "用我的口吻润色这段"。不需要手填敏感词，也不需要手动分类。

- **自动去噪**：子代理会话、非交互调用（sdk、`codex exec`）直接丢掉；其余消息按模板前缀重复、近似重复、结构化排版、回复太快、打字速度不像人、批量同时开会话、单消息会话、临时目录等信号打分。报告见 `corpus/denoise_report.json`，只有计数。
- **自动敏感实体**：从工作目录名、@提及、私有域名、GitHub owner、驼峰词、"XX公司/项目/团队/老师"等结构里找候选词，按出现在多少个会话里打分。高分直接脱敏，中间分由 agent 只看词表决定，拿不准就脱敏；通用技术词有白名单。结果写进可审计的 `corpus/auto_sensitive.json`（权限 0600）。
- **泄漏闸门**：`check.py --leak-gate` 保证档案里没有被脱敏的实体和隐私信息。

设计细节见 [docs/DESIGN.md](docs/DESIGN.md)。

## 和已有项目的区别
| | [Hiro-Inagawa/write-like-me](https://github.com/Hiro-Inagawa/write-like-me) | [marcusnelson/write-like-me-claude-skill](https://github.com/marcusnelson/write-like-me-claude-skill) | [Drew Hoover《Teach your agent your voice》](https://drewhoover.com/blog/teach-your-agent-your-voice/) | **本项目** |
|---|---|---|---|---|
| 语料来源 | 手动导出的聊天记录 | 用户提供的写作样本 | 用户的修改记录 | **自动读本地多个 agent 会话** |
| 语言 | 英文 | 英文 | 英文 | **中文优先**（语气词、口头禅、中英混用） |
| 隐私过滤 | — | — | — | **自动识别敏感实体 + 脱敏 + 泄漏闸门** |
| 区分人手打和自动化提示 | — | — | — | **✅ 自动去噪** |
| 口语/书面分开 | — | — | — | ✅ |
| 打分检查 | ✅ | — | — | ✅ |
| 从修改中学习 | — | — | ✅ | ✅ |

## 隐私
语料和档案只在本地，`.gitignore` 已排除 `corpus/`、`profiles/spoken.md`、`profiles/written.md`、`sensitive_words.txt`。

## License
MIT
