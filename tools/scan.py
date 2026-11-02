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
    # If no section's items actually changed, leave all files untouched so the
    # hourly job produces no empty churn commits.
    prev_items = {k: (v or {}).get("items", []) for k, v in prev.items()}
    new_items = {k: v["items"] for k, v in sections.items()}
    if prev_items == new_items:
        print("Wire scan: no content change — files untouched")
        return
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    wire = {"generated_at": now_iso(), "sections": sections}
    json.dump(wire, open(OUT, "w"), indent=1)
    print("Wire scan @", now_iso())
    for line in report:
        print(" ", line)
    publish_static(wire)

SITE = "https://bishowpratap7.github.io/thedevdesk/"

def publish_static(wire):
    """Bake the latest wire into index.html (crawlable headlines), regenerate
    feed.xml (Atom) and sitemap.xml. Runs on every scan; git decides if the
    result actually changed."""
    import html as H
    s = wire["sections"]
    gen = wire["generated_at"]
    def ul(items, fmt):
        return "<ul>" + "".join(f"<li>{fmt(i)}</li>" for i in items) + "</ul>"
    hn = (s.get("top_stories") or {}).get("items", [])
    rel = (s.get("releases") or {}).get("items", [])
    tr = (s.get("trending") or {}).get("items", [])
    cm = (s.get("community") or {}).get("items", [])
    baked = f'''<!--WIRE:START-->
  <section class="card baked" id="latest-wire" style="margin-bottom:16px">
    <h2>🗞️ Latest Headlines From the Wire</h2>
    <div class="sub">Edition of {H.escape(gen[:16].replace("T", " "))} UTC · baked in hourly by the newsroom scanner · the desks below also update live</div>
    <h3>Top Stories — Hacker News</h3>
    {ul(hn[:8], lambda i: f'<a href="{H.escape(i.get("url") or "https://news.ycombinator.com/item?id=" + str(i["id"]))}">{H.escape(i["title"])}</a> — {i.get("score", 0)} points, {i.get("comments", 0)} comments')}
    <h3>Release Radar — Latest Code Pushes</h3>
    {ul(rel, lambda r: f'<a href="{H.escape(r.get("url") or "")}">{H.escape(r["repo"])} {H.escape(r.get("tag") or "")}</a> — {H.escape(r.get("name") or "")}')}
    <h3>Trending on GitHub — New Repos by Stars</h3>
    {ul(tr[:8], lambda r: f'<a href="{H.escape(r["url"])}">{H.escape(r["full_name"])}</a> — ⭐ {r["stars"]} {("· " + H.escape(r["language"])) if r.get("language") else ""}')}
    <h3>Community Pulse — dev.to</h3>
    {ul(cm[:6], lambda a: f'<a href="{H.escape(a["url"])}">{H.escape(a["title"])}</a> — by {H.escape(a.get("author") or "")}')}
  </section>
  <!--WIRE:END-->'''
    idx_path = os.path.join(ROOT, "index.html")
    idx = open(idx_path).read()
    start = idx.index("<!--WIRE:START-->")
    end = idx.index("<!--WIRE:END-->") + len("<!--WIRE:END-->")
    open(idx_path, "w").write(idx[:start] + baked + idx[end:])

    # Atom feed from top stories + trending
    import datetime as _dt
    def ts(epoch):
        return _dt.datetime.fromtimestamp(epoch, _dt.timezone.utc).isoformat()
    entries = []
    for i in hn[:10]:
        entries.append(f'''<entry><title>{H.escape(i["title"])}</title><link href="{H.escape(i.get("url") or "")}"/><id>urn:hn:{i["id"]}</id><updated>{ts(i.get("time") or 0)}</updated><summary>Top story on Hacker News — {i.get("score", 0)} points, {i.get("comments", 0)} comments. Tracked by The Dev Desk.</summary></entry>''')
    feed = f'''<?xml version="1.0" encoding="utf-8"?>
<feed xmlns="http://www.w3.org/2005/Atom">
<title>The Dev Desk — Developer News Wire</title>
<subtitle>Tech news, code pushes, GitHub trending and the developer conversation — with Bishow Pandey</subtitle>
<link href="{SITE}feed.xml" rel="self"/><link href="{SITE}"/>
<id>{SITE}</id><updated>{gen}</updated>
<author><name>Bishow Pandey</name></author>
{chr(10).join(entries)}
</feed>
'''
    open(os.path.join(ROOT, "feed.xml"), "w").write(feed)
    sitemap = f'''<?xml version="1.0" encoding="UTF-8"?>
<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">
<url><loc>{SITE}</loc><lastmod>{gen[:10]}</lastmod><changefreq>hourly</changefreq><priority>1.0</priority></url>
</urlset>
'''
    open(os.path.join(ROOT, "sitemap.xml"), "w").write(sitemap)
    print("  static: index.html baked, feed.xml + sitemap.xml regenerated")

if __name__ == "__main__":
    main()
