# Agent 步骤：自动审阅候选敏感实体（用户无需参与）

输入：`corpus/review_candidates.json`，每项只有 `id, term, kind, df, score`——**不看原文**。
对每个词判断它是"通用技术词/常用词"（可保留）还是"可能指向具体的人、公司、产品、项目、地点"（脱敏）。

输出 `corpus/review_decisions.json`，严格按 schema：
```json
{"12": {"d": "keep", "r": "generic_tech"}, "13": {"d": "redact", "r": "org"}}
```
- `d` ∈ redact | keep；`r` ∈ generic_tech | common_word | person | org | project | place | product | other
- 只有 `r` 是 generic_tech / common_word 时 keep 才生效；拿不准就 redact。缺失、格式错误一律按 redact 处理（fail-closed）。
- 不要在回复里复述这些词，只写文件。然后运行 `python3 scripts/run.py --reviewed corpus/review_decisions.json`。
