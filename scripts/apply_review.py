#!/usr/bin/env python3
"""Merge the agent's review decisions into auto_sensitive.json (fail-closed).
Decisions file: {"<id>": {"d": "redact"|"keep", "r": "generic_tech|common_word|person|org|project|place|product|other"}}
where id is the index printed by `--export`. Anything missing/invalid stays redact."""
import argparse, json
REASONS = {"generic_tech", "common_word", "person", "org", "project", "place", "product", "other"}
KEEP_OK = {"generic_tech", "common_word"}
ap = argparse.ArgumentParser()
ap.add_argument("--sensitive", default="corpus/auto_sensitive.json")
ap.add_argument("--export", action="store_true", help="print review list (term, kind, df, score) for the agent")
ap.add_argument("--decisions")
a = ap.parse_args()
S = json.load(open(a.sensitive, encoding="utf-8"))
pend = [(i, e) for i, e in enumerate(S["entries"]) if e["decision"] == "review"]
if a.export:
    print(json.dumps([{"id": i, "term": e["term"], "kind": e["kind"], "df": e["df_sessions"], "score": e["score"]} for i, e in pend], ensure_ascii=False))
else:
    D = json.load(open(a.decisions, encoding="utf-8")) if a.decisions else {}
    for i, e in pend:
        d = D.get(str(i)) or {}
        if d.get("d") == "keep" and d.get("r") in KEEP_OK:
            e.update(decision="keep", decided_by="llm", reason=d["r"])
        else:
            e.update(decision="redact", decided_by="llm" if d else "default", reason=d.get("r") if d.get("r") in REASONS else "fail_closed")
    json.dump(S, open(a.sensitive, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    c = {}
    for e in S["entries"]: c[e["decided_by"] + "/" + e["decision"]] = c.get(e["decided_by"] + "/" + e["decision"], 0) + 1
    print(json.dumps(c))
