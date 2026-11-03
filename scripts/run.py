#!/usr/bin/env python3
"""One command, fully automatic:
  collect -> denoise -> detect entities -> (agent review, optional) -> filter -> stats -> profile-build brief.
Usage:  python3 scripts/run.py            # first pass; writes corpus/REVIEW_NEEDED if entities need review
        python3 scripts/run.py --reviewed corpus/review_decisions.json   # after agent review (or --no-llm)
Everything stays in ./corpus (git-ignored). Console output = counts only."""
import argparse, json, os, subprocess, sys
D = os.path.dirname(os.path.abspath(__file__)); C = "corpus"
def run(*args):
    out = subprocess.run([sys.executable, os.path.join(D, args[0]), *args[1:]], capture_output=True, text=True)
    if out.returncode: sys.exit(out.stderr)
    line = out.stdout.strip().splitlines()[-1] if out.stdout.strip() else "{}"
    print(f"[{args[0]}] {line}"); return line
ap = argparse.ArgumentParser()
ap.add_argument("--reviewed", help="agent decisions JSON for review-band entities")
ap.add_argument("--no-llm", action="store_true", help="skip agent review; review band is redacted (fail-closed)")
ap.add_argument("--include-suspect", action="store_true")
ap.add_argument("--profile-out", default=os.path.expanduser("~/.style-polish/spoken.md"), help="profile lives outside the repo")
a = ap.parse_args(); os.makedirs(C, exist_ok=True)
if not a.reviewed:
    run("collect.py", "--out", f"{C}/raw.jsonl")
    run("denoise.py", "--in", f"{C}/raw.jsonl", "--out", f"{C}/human.jsonl", "--report", f"{C}/denoise_report.json",
        *(["--include-suspect"] if a.include_suspect else []))
    run("detect.py", "--in", f"{C}/human.jsonl", "--out", f"{C}/auto_sensitive.json")
    pend = json.loads(subprocess.run([sys.executable, os.path.join(D, "apply_review.py"), "--export"], capture_output=True, text=True, cwd=os.getcwd()).stdout or "[]")
    if pend and not a.no_llm:
        json.dump(pend, open(f"{C}/review_candidates.json", "w", encoding="utf-8"), ensure_ascii=False)
        open(f"{C}/REVIEW_NEEDED", "w").write("see prompts/review_sensitive.md\n")
        print(f"[run] {len(pend)} entities need agent review -> follow prompts/review_sensitive.md, then: run.py --reviewed {C}/review_decisions.json")
        sys.exit(0)
run("apply_review.py", *(["--decisions", a.reviewed] if a.reviewed else []))
run("filter.py", "--in", f"{C}/human.jsonl", "--out", f"{C}/clean.jsonl", "--sensitive", f"{C}/auto_sensitive.json")
stats = subprocess.run([sys.executable, os.path.join(D, "check.py"), "--stats", f"{C}/clean.jsonl"], capture_output=True, text=True).stdout
open(f"{C}/stats.json", "w").write(stats)
if os.path.exists(f"{C}/REVIEW_NEEDED"): os.remove(f"{C}/REVIEW_NEEDED")
ap2 = a.profile_out
run("build_profile.py", "--in", f"{C}/clean.jsonl", "--out", ap2, "--sensitive", f"{C}/auto_sensitive.json")
gate = subprocess.run([sys.executable, os.path.join(D, "check.py"), "--leak-gate", ap2, "--sensitive", f"{C}/auto_sensitive.json"], capture_output=True, text=True)
print(f"[leak-gate] {gate.stdout.strip()}")
if gate.returncode: sys.exit("leak gate failed: profile NOT safe; fix and re-run")
print(f"[run] done -> profile {ap2} (leak gate passed). Agent may refine wording per prompts/build_profile.md; re-run the leak gate after edits.")
