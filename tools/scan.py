#!/usr/bin/env python3
"""The Dev Desk — wire scanner.
Fetches the public feeds the Live Wire page tracks and writes data/wire.json.
Each section fails independently: on failure the previous section data is kept
and flagged stale. Stdlib only; no API keys.
"""
import json, os, sys, urllib.request, datetime

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(ROOT, "data", "wire.json")
WATCHED = ["spring-projects/spring-boot", "kubernetes/kubernetes", "nodejs/node",
           "microsoft/vscode", "rust-lang/rust", "golang/go"]
STATUS_PAGES = [
    ("GitHub", "https://www.githubstatus.com/api/v2/status.json", "https://www.githubstatus.com"),
    ("Cloudflare", "https://www.cloudflarestatus.com/api/v2/status.json", "https://www.cloudflarestatus.com"),
    ("npm", "https://status.npmjs.org/api/v2/status.json", "https://status.npmjs.org"),
    ("Vercel", "https://www.vercel-status.com/api/v2/status.json", "https://www.vercel-status.com"),
]

def get(url, timeout=20):
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "DevDeskWire/1.0"})
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return json.loads(r.read().decode("utf-8"))
    except Exception:
        # The sandbox egress proxy drops some Python-TLS connections (notably
        # api.github.com/search). curl gets through — use it as the fallback.
        import subprocess
        out = subprocess.run(["curl", "-s", "--max-time", str(timeout), url],
                             capture_output=True, text=True)
        if out.returncode != 0 or not out.stdout:
            raise RuntimeError(f"curl fallback failed for {url}")
        return json.loads(out.stdout)

def now_iso():
    return datetime.datetime.now(datetime.timezone.utc).isoformat()

def scan_hn():
    ids = get("https://hacker-news.firebaseio.com/v0/topstories.json")
    items = []
    for i in ids[:12]:
        it = get(f"https://hacker-news.firebaseio.com/v0/item/{i}.json")
        if it and it.get("title"):
            items.append({"id": it["id"], "title": it["title"], "url": it.get("url"),
                          "score": it.get("score", 0), "by": it.get("by", ""),
                          "time": it.get("time", 0), "comments": it.get("descendants", 0)})
    return items

def scan_releases(prev_items=None):
    prev_by_repo = {r["repo"]: r for r in (prev_items or [])}
    out = []
    for repo in WATCHED:
        try:
            rels = get(f"https://api.github.com/repos/{repo}/releases?per_page=1")
            if rels:
                r = rels[0]
                out.append({"repo": repo, "tag": r.get("tag_name"), "name": r.get("name"),
                            "url": r.get("html_url"), "published_at": r.get("published_at") or r.get("created_at")})
            elif repo in prev_by_repo:
                out.append(prev_by_repo[repo])
        except Exception as e:
            print(f"  release {repo}: {e}", file=sys.stderr)
            if repo in prev_by_repo:
                out.append(prev_by_repo[repo])
    if not out:
        raise RuntimeError("no releases fetched (likely GitHub rate limit)")
    return out

def scan_trending():
    import time, urllib.parse
    since = (datetime.datetime.now(datetime.timezone.utc) - datetime.timedelta(days=7)).date().isoformat()
    q = urllib.parse.urlencode({"q": f"created:>{since}", "sort": "stars", "order": "desc", "per_page": 10})
    url = f"https://api.github.com/search/repositories?{q}"
    last = None
    for attempt in range(3):
        try:
            data = get(url)
            return [{"full_name": r["full_name"], "url": r["html_url"], "stars": r["stargazers_count"],
                     "language": r.get("language"), "description": r.get("description"),
                     "created_at": r["created_at"]} for r in data.get("items", [])]
        except Exception as e:
            last = e
            if attempt < 2:
                time.sleep(20)
    raise RuntimeError(f"trending failed after retries: {last}")

def scan_devto():
    arts = get("https://dev.to/api/articles?top=7&per_page=8")
    return [{"title": a["title"], "url": a["url"], "author": (a.get("user") or {}).get("name", ""),
             "reactions": a.get("public_reactions_count", 0), "comments": a.get("comments_count", 0),
             "published_at": a["published_at"]} for a in arts]

def scan_status():
    out = []
    for name, url, home in STATUS_PAGES:
        try:
            d = get(url)
            st = d.get("status") or {}
            out.append({"name": name, "home": home, "indicator": st.get("indicator", "unknown"),
                        "description": st.get("description", "")})
        except Exception as e:
            print(f"  status {name}: {e}", file=sys.stderr)
    if not out:
        raise RuntimeError("no status pages fetched")
    return out

def main():
    prev = {}
    if os.path.exists(OUT):
        try:
            prev = json.load(open(OUT)).get("sections", {})
        except Exception:
            prev = {}
    scanners = {"top_stories": lambda: scan_hn(),
                "releases": lambda: scan_releases((prev.get("releases") or {}).get("items")),
                "trending": scan_trending,
                "community": scan_devto, "status": scan_status}
    sections, report = {}, []
    for name, fn in scanners.items():
        try:
            sections[name] = {"fetched_at": now_iso(), "stale": False, "items": fn()}
            report.append(f"{name}: OK ({len(sections[name]['items'])})")
        except Exception as e:
            old = prev.get(name)
            if old:
                old = dict(old); old["stale"] = True
                sections[name] = old
                report.append(f"{name}: FAILED ({e}) — kept previous, marked stale")
            else:
                sections[name] = {"fetched_at": None, "stale": True, "items": []}
                report.append(f"{name}: FAILED ({e}) — no previous data")
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    json.dump({"generated_at": now_iso(), "sections": sections}, open(OUT, "w"), indent=1)
    print("Wire scan @", now_iso())
    for line in report:
        print(" ", line)

if __name__ == "__main__":
    main()
