#!/usr/bin/env python3
"""Separate human-typed messages from agent/automation-generated prompts. Fully automatic.
Scoring design (per message, additive) – see docs/DESIGN.md:
  hard drop: subagent/sidechain session, non-interactive entrypoint (sdk / codex_exec)
  +2/+3 template prefix (len>80, normalized first 48 chars in >=5 / >=20 sessions on >=3 days)
  +2   near-duplicate (5-char shingles, Jaccard>=0.8 with >=3 msgs in other sessions)
  +1.5 structured (>=2 md headings | >=2 xml tags | list lines >=50% & >=5 lines)
  +2   sent <2s after previous assistant message;  +1.5 chars/sec >15 and len>200
  +3   fan-out: >=3 sessions started within 10s with same prefix
  +1   single-user-message session;  +1 cwd in tmp dirs;  +0.5 worktree
  -1   human evidence: multi-turn session, short (<30) or refers back (这个/上面/刚才/不对)
  short (<=15 chars) repeats never get template points.
  score>=3 auto (drop), 1.5–3 suspect (drop unless --include-suspect), else human.
  session with >=60% auto -> whole session dropped.
Writes kept JSONL + denoise_report.json (counts / rule hits only, no text)."""
import argparse, json, re, collections, datetime

def ts(x):
    if x is None: return None
    try:
        if isinstance(x, (int, float)): return x / 1000 if x > 1e11 else x
        return datetime.datetime.fromisoformat(str(x).replace("Z", "+00:00")).timestamp()
    except Exception: return None

def norm(t): return re.sub(r"\s+", " ", re.sub(r"\d", "0", t.lower())).strip()
def shingles(t, k=5):
    t = re.sub(r"\s+", "", t); return {t[i:i+k] for i in range(max(len(t) - k + 1, 1))}
TMP = re.compile(r"^(/tmp|/private/var|/var/folders)|/T/")
BACKREF = re.compile(r"这个|上面|刚才|不对|还是|那个|继续")

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--in", dest="inp", default="corpus/raw.jsonl")
    ap.add_argument("--out", default="corpus/human.jsonl")
    ap.add_argument("--report", default="corpus/denoise_report.json")
    ap.add_argument("--include-suspect", action="store_true")
    a = ap.parse_args()
    rows = [json.loads(l) for l in open(a.inp, encoding="utf-8")]
    by_sess = collections.defaultdict(list)
    for i, r in enumerate(rows): by_sess[(r["source"], r.get("session"))].append(i)
    # template clusters
    pref_sess, pref_days = collections.defaultdict(set), collections.defaultdict(set)
    for r in rows:
        if len(r["text"]) > 80:
            p = norm(r["text"])[:48]; pref_sess[p].add(r.get("session")); t = ts(r.get("ts"))
            if t: pref_days[p].add(int(t // 86400))
    # near-dup index (only for medium/long msgs, bucketed by first shingle set sample for speed)
    sh = {i: shingles(r["text"]) for i, r in enumerate(rows) if len(r["text"]) > 40}
    buckets = collections.defaultdict(list)
    for i, s in sh.items():
        for g in sorted(s)[:3]: buckets[g].append(i)
    # fan-out: session start times by prefix
    starts = collections.defaultdict(list)
    for key, idx in by_sess.items():
        t = ts(rows[idx[0]].get("ts"))
        if t: starts[norm(rows[idx[0]]["text"])[:48]].append(t)
    fan = set()
    for p, ls in starts.items():
        ls.sort()
        for j in range(len(ls) - 2):
            if ls[j + 2] - ls[j] <= 10: fan.add(p); break

    hits = collections.Counter(); labels = [None] * len(rows); scores = [0.0] * len(rows)
    for i, r in enumerate(rows):
        t = r["text"]; fired = []
        if r.get("sub"): fired.append("hard_subagent")
        if r.get("auto_entry"): fired.append("hard_noninteractive")
        if fired:
            labels[i] = "auto"; hits.update(fired); continue
        sc = 0.0; n = norm(t)[:48]; sess_n = len(by_sess[(r["source"], r.get("session"))])
        if len(t) > 80 and len(t) > 15:
            ns, nd = len(pref_sess[n]), len(pref_days[n])
            if ns >= 20 and nd >= 3: sc += 3; fired.append("template20")
            elif ns >= 5 and nd >= 3: sc += 2; fired.append("template5")
        if i in sh:
            cand = {j for g in sorted(sh[i])[:3] for j in buckets[g] if j != i and rows[j].get("session") != r.get("session")}
            sim = sum(1 for j in list(cand)[:200] if len(sh[i] & sh[j]) / max(len(sh[i] | sh[j]), 1) >= 0.8)
            if sim >= 3: sc += 2; fired.append("near_dup")
        lines = t.splitlines()
        if len(re.findall(r"^#{1,6} ", t, re.M)) >= 2 or len(re.findall(r"<(\w+)[^>]*>.*?</\1>", t, re.S)) >= 2 or \
           (len(lines) >= 5 and sum(bool(re.match(r"\s*([-*]|\d+\.)\s", l)) for l in lines) / len(lines) >= 0.5):
            sc += 1.5; fired.append("structured")
        t0, tp = ts(r.get("ts")), ts(r.get("prev_ts"))
        if t0 and tp and 0 <= t0 - tp < 2: sc += 2; fired.append("fast_reply")
        if t0 and tp and t0 > tp and len(t) > 200 and len(t) / (t0 - tp) > 15: sc += 1.5; fired.append("typing_speed")
        if by_sess[(r["source"], r.get("session"))][0] == i and n in fan: sc += 3; fired.append("fanout")
        if sess_n == 1: sc += 1; fired.append("single_msg_session")
        cwd = r.get("cwd") or ""
        if TMP.search(cwd): sc += 1; fired.append("tmp_cwd")
        if "worktree" in cwd: sc += 0.5; fired.append("worktree")
        if sess_n > 1 and (len(t) < 30 or BACKREF.search(t[:40])): sc -= 1; fired.append("human_evidence")
        hits.update(fired); scores[i] = sc
        labels[i] = "auto" if sc >= 3 else "suspect" if sc >= 1.5 else "human"
    # session-level
    for key, idx in by_sess.items():
        if sum(labels[i] == "auto" for i in idx) / len(idx) >= 0.6:
            for i in idx:
                if labels[i] != "auto": labels[i] = "auto"; hits["session_mostly_auto"] += 1
    keep = {"human"} | ({"suspect"} if a.include_suspect else set())
    rep = collections.defaultdict(lambda: collections.Counter())
    with open(a.out, "w", encoding="utf-8") as o:
        for r, lab in zip(rows, labels):
            rep[r["source"]][lab] += 1
            if lab in keep:
                o.write(json.dumps({k: r[k] for k in ("source", "session", "ts", "cwd", "text") if k in r}, ensure_ascii=False) + "\n")
    hist = collections.Counter(min(int(s), 6) for s in scores)
    clusters = sorted(((len(v), len(pref_days[p])) for p, v in pref_sess.items() if len(v) >= 5), reverse=True)[:10]
    report = {"per_source": {s: dict(c) for s, c in rep.items()}, "rule_hits": dict(hits),
              "score_hist": dict(sorted(hist.items())), "top_template_clusters_sessions_days": clusters,
              "kept_labels": sorted(keep)}
    json.dump(report, open(a.report, "w"), ensure_ascii=False, indent=1)
    print(json.dumps({"per_source": report["per_source"]}, ensure_ascii=False))

if __name__ == "__main__":
    main()
