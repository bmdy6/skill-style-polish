#!/usr/bin/env python3
"""Score a draft against a profile's measurable stats.
Usage: check.py draft.txt --profile profiles/spoken.md   (reads the ```json stats``` block)
       check.py --stats corpus/clean.jsonl              (compute stats from corpus -> paste into profile)"""
import argparse, json, re, statistics

SENT = re.compile(r"[^。！？!?\n]+[。！？!?]?")
PARTICLES = ["吧", "呢", "啊", "嘛", "呀", "哈", "嗯", "哦", "啦", "呗"]
PUNCT = {"，": "，", "。": "。", "！": "！", "？": "？", "…": "…", "~": "~", ",": ",", "!": "!", "?": "?"}

def stats(text):
    sents = [s.strip() for s in SENT.findall(text) if s.strip()]
    lens = [len(s) for s in sents] or [0]
    chars = max(len(text), 1)
    cjk = len(re.findall(r"[\u4e00-\u9fff]", text))
    latin_words = len(re.findall(r"[A-Za-z]{2,}", text))
    return {
        "avg_sentence_len": round(statistics.mean(lens), 1),
        "p90_sentence_len": sorted(lens)[int(len(lens) * 0.9) - 1 if len(lens) > 1 else 0],
        "particles_per_100": round(sum(text.count(p) for p in PARTICLES) * 100 / max(cjk, 1), 2),
        "english_words_per_100cjk": round(latin_words * 100 / max(cjk, 1), 2),
        "punct_per_100": {k: round(text.count(k) * 100 / chars, 2) for k in PUNCT},
        "question_ratio": round(sum(s.endswith(("？", "?", "吗", "呢")) for s in sents) / max(len(sents), 1), 2),
    }

def load_profile(path):
    s = open(path, encoding="utf-8").read()
    m = re.search(r"```json\s*(\{.*?\})\s*```", s, re.S)
    prof = json.loads(m.group(1)) if m else {}
    banned = re.findall(r"^- ❌\s*(.+)$", s, re.M)
    return prof, banned

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("draft", nargs="?")
    ap.add_argument("--profile")
    ap.add_argument("--stats", help="corpus jsonl to compute baseline stats from")
    ap.add_argument("--leak-gate", help="profile.md to scan; exits 1 if it contains redacted entities / PII / ENTITY tags")
    ap.add_argument("--sensitive", default="corpus/auto_sensitive.json")
    a = ap.parse_args()
    if a.leak_gate:
        import os, sys
        sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
        from filter import PATTERNS
        txt = open(a.leak_gate, encoding="utf-8").read(); bad = {}
        if os.path.exists(a.sensitive):
            for e in json.load(open(a.sensitive, encoding="utf-8"))["entries"]:
                if e["decision"] != "keep" and e["term"].lower() in txt.lower(): bad["entity"] = bad.get("entity", 0) + 1
        for tag, rx in PATTERNS:
            n = len(rx.findall(txt))
            if n: bad[tag] = n
        if "[ENTITY]" in txt: bad["ENTITY_tag"] = txt.count("[ENTITY]")
        print(json.dumps({"leak_gate": "fail" if bad else "pass", "hits": bad})); raise SystemExit(1 if bad else 0)
    if a.stats:
        text = "\n".join(json.loads(l)["text"] for l in open(a.stats, encoding="utf-8"))
        print(json.dumps(stats(text), ensure_ascii=False, indent=2)); return
    draft = open(a.draft, encoding="utf-8").read()
    prof, banned = load_profile(a.profile)
    d = stats(draft); issues = []; score = 100
    def cmp(key, tol):
        nonlocal score
        if key in prof and prof[key]:
            diff = abs(d[key] - prof[key]) / max(prof[key], 1)
            if diff > tol:
                score -= min(20, int(diff * 20)); issues.append(f"{key}: 草稿 {d[key]} vs 档案 {prof[key]}")
    for k, tol in [("avg_sentence_len", .35), ("particles_per_100", .6), ("english_words_per_100cjk", .8), ("question_ratio", .8)]:
        cmp(k, tol)
    for p, v in prof.get("punct_per_100", {}).items():
        if v == 0 and d["punct_per_100"].get(p, 0) > 0:
            score -= 5; issues.append(f"用了档案里从不用的标点 {p}")
    for b in banned:
        if b.strip() and b.strip() in draft:
            score -= 10; issues.append(f"出现不喜欢的说法：{b.strip()}")
    print(json.dumps({"score": max(score, 0), "draft_stats": d, "issues": issues}, ensure_ascii=False, indent=2))

if __name__ == "__main__":
    main()
