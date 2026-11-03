# 提示词：从语料生成文风档案

输入：`corpus/clean.jsonl`（已过滤隐私）中 `source` 相同类型的消息样本（口语），或用户文章目录（书面语）。
1. 先运行 `python3 scripts/check.py --stats corpus/clean.jsonl`，把输出填进档案的 json 块。
2. 随机抽 200–400 条（太多就分批，每批总结后再合并），按 `profiles/TEMPLATE.md` 每一节总结。
   - 只描述**语言特征**，不要摘抄任何含具体人名、公司、业务、金额、地点的句子。
   - 每条特征给出频率感（"经常/偶尔"），可以用改写过的短例子，不用原句。
   - 区分"说话习惯"和"打字错误/语音输入错误"，后者不要当作风格。
3. 输出到 `profiles/spoken.md` 或 `profiles/written.md`。档案只留在本地，不要提交到仓库。
