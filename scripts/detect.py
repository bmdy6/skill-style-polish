#!/usr/bin/env python3
"""Automatic sensitive-entity detection -> auto_sensitive.json (no user input needed).
Candidates + scores (stdlib only, no segmenter):
  cwd dir / repo names +5 · @mention +4 · URL domain (non-public) / owner/repo +4
  CamelCase +2 · ALLCAPS 2-6 +1 · CJK before 公司/集团/科技/项目/团队/组/群 +3
  CJK name before 老师/总/哥/姐 +3 (+1 after 找/跟/和/问)
  df>=2 sessions +1, >=3 +2; df/sessions>30% and not cwd -> -2
  total = max source + 0.5*sum(other sources)
Decision: >=5 redact (rule) · 3–4.9 'review' (agent decides via prompts/review_sensitive.md;
fail-closed: undecided -> redact at filter time) · <3 dropped.
Generic tech / common words are zeroed by built-in stop lists."""
import argparse, json, re, os, collections, hashlib, datetime

TECH = frozenset("""agent agents skill skills python git github gitlab docker json yaml api apis llm llms claude codex cursor pi deepseek
openai gpt gemini mcp readme cli npm pnpm yarn node nodejs linux macos mac windows ios android chrome safari http https url html css js
ts typescript javascript react vue next nextjs vite tailwind sql sqlite postgres postgresql mysql redis mongodb supabase vercel aws gcp azure
cloudflare nginx bash zsh shell ssh tmux vim vscode jsonl csv pdf png jpg svg ui ux ai ml bug pr ci cd prompt token tokens model models
markdown md go rust java kotlin swift flutter dart php ruby c cpp oauth jwt ok todo wip app apps web ide sdk mvp demo test tests prod dev
grok lark feishu notion slack discord telegram wechat x twitter youtube google apple microsoft anthropic ollama hermes opencode antigravity
""".split())
COMMON_EN = frozenset("""the a an and or of to in on for with is are be this that it you i we can not no yes do does done use using new old
file files code data server client config error fix add update read write run build check list task tasks plan step page site home user users
""".split())
PATH_SKIP = frozenset("""users home tmp src projects project workspace workspaces repo repos demo test tests code documents desktop downloads
library application support private var folders dev work github gitlab apps app lib bin opt usr local share node_modules dist build""".split())
PUBLIC_DOMAINS = ("github.com", "gitlab.com", "google.com", "youtube.com", "x.com", "twitter.com", "openai.com", "anthropic.com",
                  "localhost", "example.com", "npmjs.com", "pypi.org", "wikipedia.org", "bilibili.com", "zhihu.com")
CJK_STOP = "这那该本我们你们他们开源新大小某各此每其"
ORG_RE = re.compile(r"([\u4e00-\u9fff]{2,4})(?:公司|集团|科技|团队|项目组|工作室)")
# function chars that never belong inside a proper noun
FUNC = set("个的了是在这那一做新整每些们我你他她它也就都还要会能把被和与或及等吗呢吧啊嘛之其所以为对从到给让用有没不很太更最再又")
SURNAME = set("王李张刘陈杨黄赵吴周徐孙马朱胡郭何高林罗郑梁谢宋唐许韩冯邓曹彭曾肖田董袁潘于蒋蔡余杜叶程苏魏吕丁任沈姚卢姜崔钟谭陆汪范金石廖贾夏韦付方白邹孟熊秦邱江尹薛闫段雷侯龙史陶黎贺顾毛郝龚邵万钱严覃武戴莫孔向汤")
PERSON_RE = re.compile(r"([找跟和问]?)([\u4e00-\u9fff]{1,3})(?:老师|总(?![结是体共之的计算览部线])|哥(?!们)|姐(?!妹))")

def strip_cjk(w):
    while w and w[0] in CJK_STOP: w = w[1:]
    return w if len(w) >= 2 and not (set(w) & FUNC) else ""

def person(name):
    # keep the shortest suffix starting with a common surname (王总 -> 王; 跟张三老师 -> 张三)
    for i, ch in enumerate(name):
        if ch in SURNAME and not (set(name[i:]) & FUNC): return name[i:]
    return ""

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--in", dest="inp", default="corpus/human.jsonl")
    ap.add_argument("--out", default="corpus/auto_sensitive.json")
    a = ap.parse_args()
    rows = [json.loads(l) for l in open(a.inp, encoding="utf-8")]
    nsess = max(len({r.get("session") for r in rows}), 1)
    src = collections.defaultdict(collections.Counter)   # term -> {source_kind: best score}
    kind = {}; df = collections.defaultdict(set); cwd_terms = set(); anchored = collections.Counter()
    def add(term, k, sc, sess=None):
        term = term.strip(" ./-_")
        if len(term) < 2 or (term.isascii() and len(term) < 3) or term.lower() in TECH or term.lower() in COMMON_EN or term.lower() in PATH_SKIP: return
        src[term][k] = max(src[term][k], sc); kind.setdefault(term, k); anchored[term] += 1
        if sess is not None: df[term].add(sess)
    for r in rows:
        if r.get("cwd"):
            for seg in re.split(r"[/\\]", r["cwd"])[3:]:   # skip /Users/<name>
                if seg and len(seg) >= 4 and seg.lower() not in PATH_SKIP and not seg.startswith("."):
                    add(seg, "cwd", 5, r.get("session")); cwd_terms.add(seg)
    for r in rows:
        t, s = r["text"], r.get("session")
        for m in re.findall(r"@([\w\u4e00-\u9fff.-]{2,20})", t): add(m, "mention", 4, s)
        for host, path in re.findall(r"https?://([\w.-]+)(/[\w.-]+/[\w.-]+)?", t):
            h = host.lower()
            if any(h == d or h.endswith("." + d) for d in PUBLIC_DOMAINS):
                if path and h.endswith("github.com"): add(path.strip("/").split("/")[0], "repo_owner", 4, s)
            else:
                parts = h.split("."); add(parts[-2] if len(parts) >= 2 else h, "domain", 4, s)
        for m in re.findall(r"\b[A-Z][a-z]+[A-Z][A-Za-z]+\b", t):
            segs = re.findall(r"[A-Z][a-z]*", m)
            add(m, "camel", 0.5 if all(x.lower() in COMMON_EN | TECH for x in segs) else 2, s)
        for m in re.findall(r"\b[A-Z]{2,6}\b", t): add(m, "allcaps", 1, s)
        for m in ORG_RE.findall(t):
            w = strip_cjk(m)
            if w: add(w, "cjk_org", 3, s)
        for pre, name in PERSON_RE.findall(t):
            n = person(name)
            if len(n) >= 2: add(n, "cjk_person", 4 if pre else 3, s)
    # also count df of cwd terms appearing in text
    for r in rows:
        for term in cwd_terms:
            if term in r["text"]: df[term].add(r.get("session"))
    # generality check: a real name is mostly seen in its anchored context; a common word
    # (e.g. a 2-char CJK word that happened to precede 团队) appears everywhere else too.
    nmsg = max(len(rows), 1)
    def msg_freq(term):
        p = re.compile((r"(?<![A-Za-z0-9])" + re.escape(term) + r"(?![A-Za-z0-9])") if term.isascii() else re.escape(term), re.I)
        return sum(1 for r in rows if p.search(r["text"]))
    entries = []
    for term, srcs in src.items():
        vals = sorted(srcs.values(), reverse=True)
        score = vals[0] + 0.5 * sum(vals[1:])
        d = len(df[term])
        score += 2 if d >= 3 else 1 if d >= 2 else 0
        if d / nsess > 0.3 and "cwd" not in srcs: score -= 2
        if score < 3: continue
        mf = msg_freq(term)
        generality = mf / max(anchored[term], 1)
        if "cwd" not in srcs and mf / nmsg > 0.005 and generality > 5:
            score -= 3   # used freely far more often than in name-like context -> common word
        elif "cwd" not in srcs and generality > 20 and len(term) <= 2:
            score -= 2
        if score < 3: continue
        entries.append({"term": term, "kind": kind[term], "sources": sorted(srcs), "df_sessions": d, "msg_freq": mf, "anchored": anchored[term],
                        "score": round(score, 1), "decision": "redact" if score >= 5 else "review",
                        "decided_by": "rule" if score >= 5 else "pending"})
    entries.sort(key=lambda e: -e["score"])
    out = {"version": 1, "generated_at": datetime.datetime.now().isoformat(timespec="seconds"),
           "corpus_hash": hashlib.sha256(open(a.inp, "rb").read()).hexdigest()[:16], "entries": entries}
    os.makedirs(os.path.dirname(a.out) or ".", exist_ok=True)
    with open(a.out, "w", encoding="utf-8") as f: json.dump(out, f, ensure_ascii=False, indent=1)
    os.chmod(a.out, 0o600)
    c = collections.Counter((e["kind"], e["decision"]) for e in entries)
    print(json.dumps({"candidates": len(entries), "by_kind_decision": {f"{k}/{d}": v for (k, d), v in c.items()}}))

if __name__ == "__main__":
    main()
