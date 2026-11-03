---
name: style-polish
description: 读取本地 AI agent 会话（Claude Code、Codex、Cursor、pi 等）中用户自己打的字，经隐私过滤后生成中文个人文风档案（口语/书面语分开），按档案润色文字、打分检查，并从用户的修改中持续学习。Use when the user asks to polish/rewrite text "in my voice", build a writing-style profile, or update it from edits.
---

# Style Polish

所有脚本在本技能目录下运行，语料和档案只留在本地（`corpus/`、`profiles/spoken.md`、`profiles/written.md` 已在 .gitignore）。

## 1. 采集 collect
```bash
python3 scripts/collect.py --list                 # 看各工具找到多少会话文件
python3 scripts/collect.py --out corpus/raw.jsonl # 全部已知适配器
```
- 只取用户角色的文本；跳过工具结果、命令提示、粘贴块、超长粘贴（>1500 字）和代码。
- **未知工具（fallback）**：自己找会话文件（如 `find ~ -maxdepth 5 \( -name "*.jsonl" -o -name "*.vscdb" -o -name "*.sqlite" \) -newer ~/.bashrc 2>/dev/null | grep -i <tool>`），先看几行结构（只看键，不打印内容），然后：
  - 能用通用适配器：`python3 scripts/collect.py --adapter generic --path FILE --out corpus/x.jsonl`；
  - 否则在 `scripts/collect.py` 里仿照 `Pi` 类加一个 Adapter 子类并登记到 `ADAPTERS`。
- DeepSeek 网页版没有本地存储：让用户在设置里导出数据，再 `--adapter deepseek --path export.json`。

## 2. 隐私过滤 filter
```bash
cp sensitive_words.example.txt sensitive_words.txt   # 填公司名、项目名、人名等，命中整条丢弃
python3 scripts/filter.py --in corpus/raw.jsonl --out corpus/clean.jsonl
```
脱敏密码、token、密钥、手机号、邮箱、身份证、卡号、IP。之后只用 `clean.jsonl`。向用户汇报时只报数量，不复述消息内容。

## 3. 建档 build profile
按 `prompts/build_profile.md`，以 `profiles/TEMPLATE.md` 为模板生成 `profiles/spoken.md`（聊天）；用户若提供文章目录，再单独生成 `profiles/written.md`。

## 4. 润色 polish
按 `prompts/polish.md`。聊天/消息用 spoken，文章用 written。只理顺语句，不改意思。

## 5. 检查 check
```bash
python3 scripts/check.py draft.txt --profile profiles/spoken.md
```
低于 80 分按 issues 再改。

## 6. 持续学习 learn from edits
用户改过稿子后，按 `prompts/learn_from_edits.md` 对比原稿与修改稿，把可复用的规则追加进档案。
