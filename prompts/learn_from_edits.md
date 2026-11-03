# 从修改中学习（参考 Drew Hoover, "Teach your agent your voice"）

1. 保存 AI 原稿为 `edits/<date>-ai.txt`，用户改后的版本为 `edits/<date>-user.txt`。
2. `diff -u edits/<date>-ai.txt edits/<date>-user.txt`（或 `git diff --no-index --word-diff`）。
3. 对每处改动问：这是一次性的内容修正，还是可复用的风格偏好？只保留后者。
   例："删掉了'值得注意的是'" → 新增不喜欢的说法；"把长句拆成两句" → 句长规则。
4. 把规则追加到对应档案的"从修改中学到的规则"一节，格式：`- {YYYY-MM-DD} 规则（依据：改动类型）`；
   新的不喜欢说法同时以 `- ❌` 加到对应列表。
5. 规则互相冲突时，以较新的为准并删除旧的；超过 30 条时合并归纳。
