#!/usr/bin/env python3
"""Build a style profile automatically from corpus/clean.jsonl — stats and whitelisted
patterns ONLY (no raw sentences, names or facts). Output follows profiles/TEMPLATE.md.
The agent may then refine wording of each section, but must keep it content-free and
re-run `check.py --leak-gate`."""
import argparse, json, re, collections, statistics, datetime, os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from check import stats
from detect import TECH

PHRASES = """其实 然后 就是 就是说 感觉 觉得 我觉得 可以 不要 还是 一下 可能 应该 好的 对的 是不是 怎么 为什么 什么 那个 这个
这样 那样 所以 但是 不过 而且 因为 比如 比如说 然后呢 的话 反正 主要 主要是 直接 先 再 帮我 你看看 你看一下 你觉得 我想 我想的是
有没有 能不能 可不可以 行不行 好不好 对吧 是吧 吧 呢 啊 嘛 呀 哈 嗯 哦 啦 呗 害 OK ok 好 行 嗯嗯 哈哈 继续 不对 没问题 也可以 一定 尽量
的意思 之类的 啥的 什么的 等等 呃 嗯这个 就行 就好 即可 麻烦 谢谢""".split()
OPENERS = ["你", "我", "帮我", "那", "这个", "好", "可以", "对", "嗯", "然后", "现在", "其实", "能不能", "为什么", "怎么", "继续", "不", "先", "OK"]
AI_ISMS = ["值得注意的是", "总而言之", "综上所述", "赋能", "抓手", "闭环", "首先，", "其次，", "最后，", "希望对你有帮助", "让我们", "深入探讨"]

def rate(texts, ph):
    return sum(t.count(ph) for t in texts) * 100 / max(len(texts), 1)

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--in", dest="inp", default="corpus/clean.jsonl")
    ap.add_argument("--out", default="profiles/spoken.md")
    ap.add_argument("--kind", default="spoken")
    ap.add_argument("--sensitive", default="corpus/auto_sensitive.json")
    a = ap.parse_args()
    texts = [json.loads(l)["text"] for l in open(a.inp, encoding="utf-8")]
    ents = []
    if os.path.exists(a.sensitive):
        ents = [e["term"].lower() for e in json.load(open(a.sensitive, encoding="utf-8"))["entries"] if e["decision"] != "keep"]
    safe = lambda w: not any(e == w.lower() or (not e.isascii() and e in w) or (not w.isascii() and w in e and len(w) > 1 and e == w) for e in ents)
    texts = [re.sub(r"\[[A-Z_]+\]", "", t) for t in texts]
    allt = "\n".join(texts); st = stats(allt)
    L = sorted(len(t) for t in texts) or [0]
    q = lambda p: L[min(int(len(L) * p), len(L) - 1)]
    ph = sorted(((rate(texts, p), p) for p in PHRASES), reverse=True)
    top = [(p, round(r, 1)) for r, p in ph if r >= 1 and safe(p)][:20]
    op = collections.Counter(next((o for o in sorted(OPENERS, key=len, reverse=True) if t.startswith(o)), None) for t in texts)
    op.pop(None, None)
    endp = collections.Counter((t.rstrip()[-1:] if t.rstrip() and not re.match(r"[\w\u4e00-\u9fff]", t.rstrip()[-1:]) else "无标点") for t in texts)
    eng = collections.Counter(w.lower() for w in re.findall(r"[A-Za-z]{2,}", allt) if w.lower() in TECH)
    space_en = len(re.findall(r"[\u4e00-\u9fff] [A-Za-z]", allt)); nospace_en = len(re.findall(r"[\u4e00-\u9fff][A-Za-z]", allt))
    multi_line = sum("\n" in t for t in texts) / max(len(texts), 1)
    lists = sum(bool(re.search(r"^\s*([-*]|\d+[.、])\s", t, re.M)) for t in texts) / max(len(texts), 1)
    used_ai = [x for x in AI_ISMS if rate(texts, x) < 0.2]
    js = {k: st[k] for k in ("avg_sentence_len", "particles_per_100", "english_words_per_100cjk", "question_ratio", "punct_per_100")}
    md = f"""# 文风档案：{a.kind}

> 自动生成于 {datetime.date.today()}，样本 {len(texts)} 条消息。只含统计和白名单模式，不含原文。

## 可度量统计
```json
{json.dumps(js, ensure_ascii=False)}
```

## 用词
- 高频口语词/连接词（每 100 条消息出现次数）：{", ".join(f"{p} {r}" for p, r in top)}

## 句长与节奏
- 单条消息长度 p10/p50/p90：{q(.1)}/{q(.5)}/{q(.9)} 字；平均句长 {st['avg_sentence_len']} 字，p90 句长 {st['p90_sentence_len']} 字
- 多行消息占比 {multi_line:.0%}

## 语气词
- 每 100 个汉字语气词 {st['particles_per_100']} 个；问句比例 {st['question_ratio']:.0%}

## 口头禅
- 常见开头：{", ".join([f"{o}…（{c * 100 // max(len(texts), 1)}%）" for o, c in op.most_common(12) if safe(o)][:8])}

## 中英混用
- 每 100 个汉字英文词 {st['english_words_per_100cjk']} 个；常用英文技术词：{", ".join([w for w, _ in eng.most_common(30) if safe(w)][:12])}
- 中文后接英文时加空格的比例 {space_en / max(space_en + nospace_en, 1):.0%}

## 标点习惯
- 每 100 字标点：{", ".join(f"{k} {v}" for k, v in st['punct_per_100'].items() if v)}
- 消息结尾：{", ".join(f"{k} {c * 100 // max(len(texts), 1)}%" for k, c in endp.most_common(5))}

## 结构习惯
- 含列表的消息占比 {lists:.0%}

## 不喜欢的说法（几乎从不使用，check.py 会扣分）
""" + "\n".join(f"- ❌ {x}" for x in used_ai) + "\n\n## 从修改中学到的规则\n"
    # final self-sanitize with exactly the leak-gate matching rules
    for e in ents:
        rx = (r"(?<![A-Za-z0-9])" + re.escape(e) + r"(?![A-Za-z0-9])") if e.isascii() else re.escape(e)
        md = re.sub(rx, "⟨略⟩", md, flags=re.I)
    os.makedirs(os.path.dirname(a.out) or ".", exist_ok=True)
    open(a.out, "w", encoding="utf-8").write(md)
    print(json.dumps({"profile": a.out, "samples": len(texts), "sections": re.findall(r"^## (.+)$", md, re.M)}, ensure_ascii=False))

if __name__ == "__main__":
    main()
