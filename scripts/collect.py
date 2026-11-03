#!/usr/bin/env python3
"""Collect ONLY the user's own typed messages from local AI-agent sessions.

Plugin-style: each adapter = class with name, default_globs(), parse(path) -> iter of dict.
Output: JSONL corpus, one {"source","session","ts","text"} per line.

Status:
  claude   TESTED   ~/.claude/projects/*/*.jsonl
  codex    UNTESTED ~/.codex/sessions/**/rollout-*.jsonl   (format from Codex CLI source/docs)
  pi       UNTESTED ~/.pi/agent/sessions/**/*.jsonl        (pi-mono coding agent)
  cursor   UNTESTED Cursor state.vscdb (SQLite, cursorDiskKV bubbleId:* rows, type==1 = user)
  deepseek UNTESTED DeepSeek web has no local store; point --path at an exported JSON
  generic  fallback: --adapter generic --path FILE, heuristic role=user extraction
"""
import argparse, glob, json, os, re, sqlite3, sys

H = os.path.expanduser
MAX_LEN = 1500          # longer = probably a paste
CODE_RE = re.compile(r"```|^\s*(def |class |import |function |const |let |#include|SELECT |<\w+[^>]*>)", re.M)
NOISE_PREFIX = ("<command-", "<local-command", "Caveat:", "<system-reminder", "<environment_context",
                "<user_instructions", "[Request interrupted", "This session is being continued")

def clean(text, max_len=MAX_LEN):
    """Return the text if it looks like something the user typed, else None."""
    if not isinstance(text, str):
        return None
    t = re.sub(r"\[Pasted text #\d+[^\]]*\]", "", text).strip()
    if not t or t.startswith(NOISE_PREFIX):
        return None
    if len(t) > max_len or CODE_RE.search(t):
        return None
    lines = t.splitlines()
    if len(lines) > 3 and sum(1 for l in lines if re.search(r"[{};=]\s*$|^\s{4,}", l)) / len(lines) > 0.3:
        return None  # looks like a log / code paste
    return t

def texts_from_content(content):
    if isinstance(content, str):
        yield content
    elif isinstance(content, list):
        for b in content:
            if isinstance(b, dict) and b.get("type") in ("text", "input_text"):
                yield b.get("text", "")

def jsonl(path):
    with open(path, encoding="utf-8", errors="ignore") as f:
        for line in f:
            try:
                yield json.loads(line)
            except Exception:
                continue

class Adapter:
    name = "base"; tested = False; globs = []
    def default_paths(self):
        out = []
        for g in self.globs:
            out += glob.glob(H(g), recursive=True)
        return sorted(set(out))
    def parse(self, path):
        raise NotImplementedError

class Claude(Adapter):
    name, tested, globs = "claude", True, ["~/.claude/projects/*/*.jsonl"]
    def parse(self, path):
        for d in jsonl(path):
            if d.get("type") != "user" or d.get("isMeta") or d.get("isCompactSummary") or d.get("toolUseResult") is not None:
                continue
            m = d.get("message") or {}
            if m.get("role") != "user":
                continue
            c = m.get("content")
            if isinstance(c, list) and any(isinstance(b, dict) and b.get("type") in ("tool_result", "pasted_content") for b in c):
                continue
            for t in texts_from_content(c):
                yield {"session": d.get("sessionId"), "ts": d.get("timestamp"), "text": t}

class Codex(Adapter):
    name, globs = "codex", ["~/.codex/sessions/**/*.jsonl"]
    def parse(self, path):
        seen_event = False; items = []
        for d in jsonl(path):
            p = d.get("payload") if isinstance(d.get("payload"), dict) else d
            if d.get("type") == "event_msg" and p.get("type") == "user_message":
                seen_event = True
                yield {"session": os.path.basename(path), "ts": d.get("timestamp"), "text": p.get("message", "")}
            elif p.get("type") == "message" and p.get("role") == "user":
                for t in texts_from_content(p.get("content")):
                    items.append({"session": os.path.basename(path), "ts": d.get("timestamp"), "text": t})
        if not seen_event:          # older rollouts only have response items
            yield from items

class Pi(Adapter):
    name, globs = "pi", ["~/.pi/agent/sessions/**/*.jsonl"]
    def parse(self, path):
        for d in jsonl(path):
            m = d.get("message") if isinstance(d.get("message"), dict) else d
            if m.get("role") == "user":
                for t in texts_from_content(m.get("content")):
                    yield {"session": os.path.basename(path), "ts": d.get("timestamp"), "text": t}

class Cursor(Adapter):
    name = "cursor"
    globs = ["~/.config/Cursor/User/globalStorage/state.vscdb",
             "~/Library/Application Support/Cursor/User/globalStorage/state.vscdb",
             "~/AppData/Roaming/Cursor/User/globalStorage/state.vscdb"]
    def parse(self, path):
        try:
            con = sqlite3.connect(f"file:{path}?mode=ro", uri=True)
            rows = con.execute("SELECT key, value FROM cursorDiskKV WHERE key LIKE 'bubbleId:%'").fetchall()
        except Exception as e:
            print(f"[cursor] cannot read {path}: {e}", file=sys.stderr); return
        for k, v in rows:
            try:
                b = json.loads(v)
            except Exception:
                continue
            if b.get("type") == 1:   # 1 = user, 2 = assistant
                yield {"session": k.split(":")[1] if ":" in k else None, "ts": None, "text": b.get("text", "")}

class Generic(Adapter):
    """Fallback for unknown tools / exports (DeepSeek, ChatGPT export...). Walks any JSON(L)
    and yields strings under objects whose role/author/type marks them as the user."""
    name = "generic"
    USER = {"user", "human", "REQUEST"}
    def _walk(self, o):
        if isinstance(o, dict):
            author = o.get("author")
            role = o.get("role") or (author.get("role") if isinstance(author, dict) else None)
            if role in self.USER or o.get("type") in self.USER:
                for key in ("content", "text", "message"):
                    if key in o:
                        v = o[key]
                        if isinstance(v, dict) and "parts" in v:
                            v = " ".join(x for x in v["parts"] if isinstance(x, str))
                        yield from texts_from_content(v)
                        break
            for v in o.values():
                if isinstance(v, (dict, list)): yield from self._walk(v)
        elif isinstance(o, list):
            for v in o: yield from self._walk(v)
    def parse(self, path):
        docs = list(jsonl(path)) if path.endswith(".jsonl") else [json.load(open(path, encoding="utf-8"))]
        for d in docs:
            for t in self._walk(d):
                yield {"session": os.path.basename(path), "ts": None, "text": t}

class DeepSeek(Generic):
    name = "deepseek"; globs = []   # web export only; use --path

ADAPTERS = {a.name: a for a in (Claude(), Codex(), Pi(), Cursor(), DeepSeek(), Generic())}

def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--adapter", action="append", help="adapter(s) to run; default all with default paths")
    ap.add_argument("--path", action="append", help="explicit file(s) for the chosen adapter")
    ap.add_argument("--out", default="corpus/raw.jsonl")
    ap.add_argument("--max-len", type=int, default=MAX_LEN)
    ap.add_argument("--list", action="store_true", help="only list discovered session files per adapter")
    a = ap.parse_args()
    names = a.adapter or [n for n in ADAPTERS if ADAPTERS[n].globs]
    os.makedirs(os.path.dirname(a.out) or ".", exist_ok=True)
    counts, seen = {}, set()
    with open(a.out, "w", encoding="utf-8") as out:
        for n in names:
            ad = ADAPTERS[n]
            paths = a.path or ad.default_paths()
            if a.list:
                print(f"{n}: {len(paths)} files"); continue
            c = 0
            for p in paths:
                for r in ad.parse(p):
                    t = clean(r["text"], a.max_len)
                    if not t or t in seen: continue
                    seen.add(t); c += 1
                    out.write(json.dumps({"source": n, **r, "text": t}, ensure_ascii=False) + "\n")
            counts[n] = c
    if not a.list:
        print(json.dumps({"files_out": a.out, "messages_per_source": counts}, ensure_ascii=False))

if __name__ == "__main__":
    main()
