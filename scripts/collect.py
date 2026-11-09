#!/usr/bin/env python3
"""Collect ONLY the user's own typed messages from local AI-agent sessions.

Plugin-style: each adapter = class with name, default_globs(), parse(path) -> iter of dict.
Output: JSONL corpus, one {"source","session","ts","text"} per line.

Status:
  claude   TESTED   ~/.claude/projects/*/*.jsonl
  codex    TESTED   ~/.codex/sessions/**/rollout-*.jsonl
  pi       TESTED   ~/.pi/agent/sessions/**/*.jsonl
  cursor   TESTED   ~/.cursor/projects/*/agent-transcripts + Cursor state.vscdb
  deepseek TESTED   ~/.deepseek/sessions/*.json (DeepSeek Harness); web: export + generic
  opencode TESTED   ~/.local/share/opencode/opencode.db
  generic  fallback: --adapter generic --path FILE, heuristic role=user extraction
"""
import argparse, glob, json, os, re, sqlite3, sys
from collections import Counter
from contextlib import closing
from pathlib import Path

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

def jsonl(path, warn=None):
    with open(path, encoding="utf-8", errors="ignore") as f:
        for line in f:
            try:
                yield json.loads(line)
            except (ValueError, RecursionError) as exc:
                if warn: warn("record_error:" + type(exc).__name__)
                continue

class Adapter:
    name = "base"; tested = False; globs = []
    def __init__(self):
        self.warnings = Counter()
    def warn(self, reason):
        # Never include paths, exception messages or source text in diagnostics.
        self.warnings[reason] += 1
    def object(self, value):
        if isinstance(value, dict): return value
        self.warn("invalid_object")
        return {}
    def objects(self, values):
        if not isinstance(values, list):
            self.warn("invalid_list")
            return
        for value in values:
            yield self.object(value)
    def records(self, path):
        for value in jsonl(path, self.warn):
            yield self.object(value)
    def decode(self, raw):
        try:
            return json.loads(raw)
        except (ValueError, TypeError, RecursionError) as exc:
            self.warn("record_error:" + type(exc).__name__)
            return None
    def texts(self, content):
        if not isinstance(content, (str, list)):
            self.warn("invalid_content")
            return
        for text in texts_from_content(content):
            if isinstance(text, str): yield text
            else: self.warn("invalid_text")
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
        last_asst = None
        for d in self.records(path):
            if d.get("type") == "assistant":
                last_asst = d.get("timestamp")
            if d.get("type") != "user" or d.get("isMeta") or d.get("isCompactSummary") or d.get("toolUseResult") is not None:
                continue
            m = self.object(d.get("message"))
            if m.get("role") != "user":
                continue
            c = m.get("content")
            if isinstance(c, list) and any(isinstance(b, dict) and b.get("type") in ("tool_result", "pasted_content") for b in c):
                continue
            for t in self.texts(c):
                yield {"session": d.get("sessionId"), "ts": d.get("timestamp"), "text": t,
                       "cwd": d.get("cwd"), "sub": bool(d.get("isSidechain")), "prev_ts": last_asst,
                       "auto_entry": d.get("entrypoint") in ("sdk-cli", "sdk-ts", "sdk-py")}

class Codex(Adapter):
    """TESTED (macOS, Codex CLI/App 2026-10). Newer rollouts carry the typed prompt in
    event_msg/item_completed item.type=UserMessage; some versions use event_msg/user_message;
    response_item/message role=user also contains injected AGENTS.md / environment context,
    so it is only a last-resort fallback."""
    name, tested, globs = "codex", True, ["~/.codex/sessions/**/*.jsonl"]
    def parse(self, path):
        um, ev, ri = [], [], []
        sid = os.path.basename(path); meta = {}; last_asst = None
        for d in self.records(path):
            p = self.object(d["payload"]) if "payload" in d else d
            ts = d.get("timestamp")
            if d.get("type") == "session_meta":
                meta = {"cwd": p.get("cwd"), "auto_entry": p.get("originator") in ("codex_exec", "codex_sdk_ts"),
                        "sub": bool(p.get("source") not in (None, "cli", "vscode", "exec") and isinstance(p.get("source"), dict))}
            if p.get("type") == "message" and p.get("role") == "assistant":
                last_asst = ts
            if p.get("type") == "item_completed":
                item = self.object(p.get("item"))
                if item.get("type") == "UserMessage":
                    for t in self.texts(item.get("content")):
                        um.append({"session": sid, "ts": ts, "text": t, "prev_ts": last_asst})
            elif d.get("type") == "event_msg" and p.get("type") == "user_message":
                ev.append({"session": sid, "ts": ts, "text": p.get("message", ""), "prev_ts": last_asst})
            elif p.get("type") == "message" and p.get("role") == "user":
                for t in self.texts(p.get("content")):
                    ri.append({"session": sid, "ts": ts, "text": t, "prev_ts": last_asst})
        for r in (um or ev or ri):
            yield {**meta, **r}

class Pi(Adapter):
    """TESTED (pi coding agent): {"type":"message","message":{"role":"user","content":[{"type":"text"}]}}.
    toolResult / custom_message / compaction entries are skipped."""
    name, tested, globs = "pi", True, ["~/.pi/agent/sessions/**/*.jsonl"]
    def parse(self, path):
        meta, last_asst = {}, None
        for d in self.records(path):
            if d.get("type") == "session":
                meta = {"cwd": d.get("cwd"), "sub": bool(d.get("parentSession"))}
            if d.get("type") != "message": continue
            m = self.object(d.get("message"))
            if m.get("role") == "assistant":
                last_asst = d.get("timestamp")
            if m.get("role") == "user":
                for t in self.texts(m.get("content")):
                    yield {**meta, "session": os.path.basename(path), "ts": d.get("timestamp"), "text": t, "prev_ts": last_asst}

class DeepSeek(Adapter):
    """TESTED (DeepSeek Harness / ~/.deepseek/sessions/*.json): {"messages":[{"role","content":[blocks]}]}.
    user turns that are tool_result blocks are skipped. DeepSeek *web* has no local store:
    export it and use --adapter generic --path export.json."""
    name, tested, globs = "deepseek", True, ["~/.deepseek/sessions/*.json"]
    def parse(self, path):
        with open(path, encoding="utf-8") as f:
            d = self.object(json.load(f))
        for m in self.objects(d.get("messages", [])):
            if m.get("role") != "user": continue
            c = m.get("content")
            if isinstance(c, list) and any(isinstance(b, dict) and b.get("type") == "tool_result" for b in c): continue
            for t in self.texts(c):
                yield {"session": os.path.basename(path), "ts": None, "text": t}

def ro_sqlite(path):
    # Live stores are not immutable: committed pages may still be in the WAL.
    # One transaction keeps multi-query adapters on the same committed snapshot.
    con = sqlite3.connect(Path(path).resolve().as_uri() + "?mode=ro", uri=True)
    try:
        con.execute("BEGIN")
    except Exception:
        con.close()
        raise
    return con

UQ = re.compile(r"<user_query>\s*(.*?)\s*</user_query>", re.S)

class Cursor(Adapter):
    """TESTED (Cursor 2026, macOS). Three stores:
    1. ~/.cursor/projects/*/agent-transcripts/**/*.jsonl  {"role":"user","message":{"content":[text]}}; text in <user_query>
    2. workspaceStorage/*/state.vscdb ItemTable 'aiService.prompts' (list of {text, commandType})
    3. globalStorage/state.vscdb cursorDiskKV 'bubbleId:*' with type==1 (often empty: newer
       versions keep only assistant bubbles locally / encrypt conversation blobs)."""
    name, tested = "cursor", True
    SUPPORT = ["~/Library/Application Support/Cursor", "~/.config/Cursor", "~/AppData/Roaming/Cursor"]
    globs = ["~/.cursor/projects/*/agent-transcripts/**/*.jsonl"] + \
            [b + "/User/globalStorage/state.vscdb" for b in SUPPORT] + \
            [b + "/User/workspaceStorage/*/state.vscdb" for b in SUPPORT]
    def parse(self, path):
        sid = os.path.basename(os.path.dirname(path))
        if path.endswith(".jsonl"):
            for d in self.records(path):
                if d.get("role") != "user": continue
                m = d.get("message"); c = m.get("content") if isinstance(m, dict) else m
                for t in self.texts(c):
                    q = UQ.search(t)
                    yield {"session": sid, "ts": None, "text": q.group(1) if q else t}
            return
        with closing(ro_sqlite(path)) as con:
            if "workspaceStorage" in path:
                for (v,) in con.execute("SELECT value FROM ItemTable WHERE key='aiService.prompts'"):
                    for x in self.objects(self.decode(v)):
                        yield {"session": sid, "ts": None, "text": x.get("text", "")}
            else:
                for k, v in con.execute("SELECT key, value FROM cursorDiskKV WHERE key LIKE 'bubbleId:%'"):
                    b = self.object(self.decode(v))
                    if b.get("type") == 1:
                        yield {"session": k.split(":")[1], "ts": None, "text": b.get("text", "")}

class OpenCode(Adapter):
    """TESTED (opencode, ~/.local/share/opencode/opencode.db): message.data.role=='user',
    text in part.data where type=='text'."""
    name, tested, globs = "opencode", True, ["~/.local/share/opencode/opencode.db"]
    def parse(self, path):
        with closing(ro_sqlite(path)) as con:
            users = {i for i, d in con.execute("SELECT id, data FROM message")
                     if self.object(self.decode(d)).get("role") == "user"}
            for mid, sid, d in con.execute("SELECT message_id, session_id, data FROM part ORDER BY time_created"):
                p = self.object(self.decode(d))
                if mid in users and p.get("type") == "text" and not p.get("synthetic"):
                    yield {"session": sid, "ts": None, "text": p.get("text", "")}

# NOT SUPPORTED: Google Antigravity (~/.gemini/antigravity*/conversations/*.db) stores steps as
# protobuf blobs; Gemini CLI (~/.gemini/tmp/*/chats/*.json) can be tried with --adapter generic.

class Generic(Adapter):
    """Fallback for unknown tools / exports (DeepSeek, ChatGPT export...). Walks any JSON(L)
    and yields strings under objects whose role/author/type marks them as the user."""
    name = "generic"
    USER = ("user", "human", "REQUEST")
    def _walk(self, o):
        if isinstance(o, dict):
            author = o.get("author")
            role = o.get("role") or (author.get("role") if isinstance(author, dict) else None)
            if role in self.USER or o.get("type") in self.USER:
                for key in ("content", "text", "message"):
                    if key in o:
                        v = o[key]
                        if isinstance(v, dict) and "parts" in v:
                            parts = v["parts"]
                            if not isinstance(parts, list):
                                self.warn("invalid_content")
                                break
                            v = " ".join(x for x in parts if isinstance(x, str))
                        yield from self.texts(v)
                        break
            for v in o.values():
                if isinstance(v, (dict, list)): yield from self._walk(v)
        elif isinstance(o, list):
            for v in o: yield from self._walk(v)
    def parse(self, path):
        if path.endswith(".jsonl"):
            docs = jsonl(path, self.warn)
        else:
            with open(path, encoding="utf-8") as f:
                docs = [json.load(f)]
        for d in docs:
            for t in self._walk(d):
                yield {"session": os.path.basename(path), "ts": None, "text": t}

ADAPTERS = {a.name: a for a in (Claude(), Codex(), Pi(), Cursor(), DeepSeek(), OpenCode(), Generic())}

def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--adapter", action="append", choices=tuple(ADAPTERS), help="adapter(s) to run; default all with default paths")
    ap.add_argument("--path", action="append", help="explicit file(s) for the chosen adapter")
    ap.add_argument("--out", default="corpus/raw.jsonl")
    ap.add_argument("--max-len", type=int, default=MAX_LEN)
    ap.add_argument("--max-template-repeat", type=int, default=0,
                    help="drop messages whose first 30 chars repeat more than N times (automated/template prompts)")
    ap.add_argument("--list", action="store_true", help="only list discovered session files per adapter")
    a = ap.parse_args()
    names = a.adapter or [n for n in ADAPTERS if ADAPTERS[n].globs]
    os.makedirs(os.path.dirname(a.out) or ".", exist_ok=True)
    counts, seen, rows = {}, set(), []
    warnings = {}
    for n in names:
        ad = ADAPTERS[n]
        ad.warnings.clear()
        paths = a.path or ad.default_paths()
        if a.list:
            print(f"{n}: {len(paths)} files"); continue
        c = 0
        for p in paths:
            try:
                for r in ad.parse(p):
                    if not isinstance(r.get("text"), str):
                        ad.warn("invalid_text")
                        continue
                    t = clean(r["text"], a.max_len)
                    if not t: continue
                    for field in ("session", "ts", "prev_ts", "cwd"):
                        allowed = (str,) if field == "cwd" else (str, int, float)
                        if r.get(field) is not None and not isinstance(r[field], allowed):
                            ad.warn("invalid_metadata")
                            r[field] = None
                    key = (r.get("session"), t)
                    if key in seen: continue
                    seen.add(key); c += 1
                    rows.append({"source": n, **r, "text": t})
            except Exception as exc:
                # Isolate unreadable files and unexpected format changes, keeping
                # healthy files/sources. Exception text can contain private data.
                ad.warn("file_error:" + type(exc).__name__)
        counts[n] = c
        if ad.warnings: warnings[n] = dict(ad.warnings)
    pref = Counter(r["text"][:30] for r in rows)
    dropped = Counter()
    with open(a.out, "w", encoding="utf-8") as out:
        for r in rows:
            if a.max_template_repeat and pref[r["text"][:30]] > a.max_template_repeat:
                dropped[r["source"]] += 1; counts[r["source"]] -= 1; continue
            out.write(json.dumps(r, ensure_ascii=False) + "\n")
    if not a.list:
        print(json.dumps({"files_out": a.out, "messages_per_source": counts,
                          "dropped_as_template": dict(dropped), "warnings_per_source": warnings}, ensure_ascii=False))

if __name__ == "__main__":
    main()
