#!/usr/bin/env python3
"""Privacy filter: redact secrets/PII; drop whole message if it hits the sensitive-word list
or looks like it is mostly credentials. Prints only counts."""
import argparse, json, re

PATTERNS = [
    ("PRIVATE_KEY", re.compile(r"-----BEGIN [A-Z ]*PRIVATE KEY-----")),
    ("TOKEN", re.compile(r"\b(sk-[A-Za-z0-9_-]{16,}|gh[pousr]_[A-Za-z0-9]{20,}|xox[abpr]-[A-Za-z0-9-]{10,}|AKIA[0-9A-Z]{16}|eyJ[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]+)")),
    ("SECRET", re.compile(r"(?i)(password|passwd|pwd|密码|口令|token|secret|api[_-]?key|密钥)\s*[:：=是为]\s*\S+")),
    ("EMAIL", re.compile(r"[\w.+-]+@[\w-]+\.[\w.-]+")),
    ("ID_CN", re.compile(r"\b\d{17}[\dXx]\b")),
    ("CARD", re.compile(r"\b(?:\d[ -]?){13,19}\b")),
    ("PHONE", re.compile(r"(?<!\d)(?:\+?86[- ]?)?1[3-9]\d{9}(?!\d)|\+\d{1,3}[- ]?\d{3,4}[- ]?\d{3,4}[- ]?\d{3,4}")),
    ("IP", re.compile(r"\b(?:\d{1,3}\.){3}\d{1,3}\b")),
    ("LONGKEY", re.compile(r"\b(?=[A-Za-z0-9]*\d)(?=[A-Za-z0-9]*[A-Za-z])[A-Za-z0-9_\-!@#$%]{16,}\b")),
]

def load_words(path):
    if not path: return []
    with open(path, encoding="utf-8") as f:
        return [w.strip().lower() for w in f if w.strip() and not w.startswith("#")]

def redact(text):
    hits = 0
    for tag, rx in PATTERNS:
        text, n = rx.subn(f"[{tag}]", text); hits += n
    return text, hits

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--in", dest="inp", default="corpus/raw.jsonl")
    ap.add_argument("--out", default="corpus/clean.jsonl")
    ap.add_argument("--words", default="sensitive_words.txt", help="one word per line; hit = drop message")
    a = ap.parse_args()
    try: words = load_words(a.words)
    except FileNotFoundError: words = []
    st = {"in": 0, "kept": 0, "dropped_word": 0, "dropped_secret_heavy": 0, "redactions": 0}
    with open(a.inp, encoding="utf-8") as f, open(a.out, "w", encoding="utf-8") as o:
        for line in f:
            r = json.loads(line); st["in"] += 1
            low = r["text"].lower()
            if any(w in low for w in words):
                st["dropped_word"] += 1; continue
            t, h = redact(r["text"])
            plain = re.sub(r"\[[A-Z_]+\]", "", t)
            if h and len(plain.strip()) < 0.4 * len(r["text"]):
                st["dropped_secret_heavy"] += 1; continue
            st["redactions"] += h; st["kept"] += 1
            r["text"] = t
            o.write(json.dumps(r, ensure_ascii=False) + "\n")
    print(json.dumps(st))

if __name__ == "__main__":
    main()
