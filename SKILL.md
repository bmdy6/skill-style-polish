---
name: style-polish
description: 读取本地 AI agent 会话（Claude Code、Codex、Cursor、pi 等）中用户自己打的字，经隐私过滤后生成中文个人文风档案（口语/书面语分开），按档案润色文字、打分检查，并从用户的修改中持续学习。Use when the user asks to polish/rewrite text "in my voice", build a writing-style profile, or update it from edits.
---

# Style Polish

所有脚本在本技能目录下运行。语料、`auto_sensitive.json` 和档案都只留在本地，已在 .gitignore 里排除。

## 1. 一条命令全自动处理（用户无需填写或分类任何东西）
```bash
python3 scripts/run.py
```
它依次执行：采集（collect）→ 去噪（denoise：区分人手打的消息和 agent/自动化生成的提示）→ 自动发现敏感实体（detect → `corpus/auto_sensitive.json`）→ 隐私过滤（filter）→ 统计（stats）。终端只输出数量。

如果输出提示 `entities need agent review`：
1. 按 `prompts/review_sensitive.md` 自己审阅 `corpus/review_candidates.json`（只有词、类型、计数，没有原文），写出 `corpus/review_decisions.json`。拿不准就 redact。**不要问用户，也不要在回复里复述这些词。**
2. 运行 `python3 scripts/run.py --reviewed corpus/review_decisions.json`。

没有 LLM 时可用 `--no-llm`：待审的词一律脱敏。

- 认不出的工具：自己找会话文件，只看键名不看内容；能用就 `collect.py --adapter generic --path FILE`，不能用就在 `collect.py` 里仿照 `Pi` 加一个适配器。
- 向用户汇报时只报各来源保留/丢弃的数量，不复述消息内容。

## 2. 档案只存风格，不存事实
- 只写统计量和抽象模式（句长、语气词、标点、中英混用比例、口头禅、开头和结尾惯用语）。
- 举例必须用槽位模板，例如"帮我把 ⟨X⟩ 改成 ⟨Y⟩"，不能出现具体的名字、项目、金额、地点。
- 写完必须过泄漏闸门：`python3 scripts/check.py --leak-gate profiles/spoken.md`，不通过就改到通过为止。

## 3. 建档 build profile
用 `corpus/clean.jsonl` 和 `corpus/stats.json`，按 `prompts/build_profile.md`，以 `profiles/TEMPLATE.md` 为模板生成 `profiles/spoken.md`（聊天）；用户若提供文章目录，再单独生成 `profiles/written.md`。

## 4. 润色 polish
按 `prompts/polish.md`。聊天/消息用 spoken，文章用 written。只理顺语句，不改意思。

## 5. 检查 check
```bash
python3 scripts/check.py draft.txt --profile profiles/spoken.md
```
低于 80 分按 issues 再改。

## 6. 持续学习 learn from edits
用户改过稿子后，按 `prompts/learn_from_edits.md` 对比原稿与修改稿，把可复用的规则追加进档案。
