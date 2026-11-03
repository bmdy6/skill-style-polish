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

自动化/模板化提示（前 30 字重复超过 15 次，比如子代理任务模板）会被自动丢弃，可用 `--max-template-repeat` 调整。

## 安装
```bash
git clone https://github.com/bmdy6/skill-style-polish ~/.claude/skills/style-polish
```
只依赖 Python 3 标准库。

## 使用
```bash
cd ~/.claude/skills/style-polish
python3 scripts/collect.py --out corpus/raw.jsonl
cp sensitive_words.example.txt sensitive_words.txt   # 填公司名等
python3 scripts/filter.py
python3 scripts/check.py --stats corpus/clean.jsonl
```
然后对 agent 说："按我的文风建档" / "用我的口吻润色这段"。

## 和已有项目的区别
| | [Hiro-Inagawa/write-like-me](https://github.com/Hiro-Inagawa/write-like-me) | [marcusnelson/write-like-me-claude-skill](https://github.com/marcusnelson/write-like-me-claude-skill) | [Drew Hoover《Teach your agent your voice》](https://drewhoover.com/blog/teach-your-agent-your-voice/) | **本项目** |
|---|---|---|---|---|
| 语料来源 | 手动导出的聊天记录 | 用户提供的写作样本 | 用户的修改记录 | **自动读本地多个 agent 会话** |
| 语言 | 英文 | 英文 | 英文 | **中文优先**（语气词、口头禅、中英混用） |
| 隐私过滤 | — | — | — | **脱敏 + 敏感词整条丢弃** |
| 口语/书面分开 | — | — | — | ✅ |
| 打分检查 | ✅ | — | — | ✅ |
| 从修改中学习 | — | — | ✅ | ✅ |

## 隐私
语料和档案只在本地，`.gitignore` 已排除 `corpus/`、`profiles/spoken.md`、`profiles/written.md`、`sensitive_words.txt`。

## License
MIT
