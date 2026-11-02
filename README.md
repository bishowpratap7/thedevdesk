# The Dev Desk — Live Developer News Wire

A developer news channel by **Bishow Pandey** — "CNN for developers": tech news, code pushes,
trending repos, and what developers are saying on public forums, tracked live and shown on
one static page.

## What's here
- `index.html` — the Live Wire page (v0.1 prototype). A single static file, no build step,
  no backend, no API keys. Open it in a browser or serve it with any static host.
- It pulls live from public feeds in the visitor's browser and auto-refreshes every 5 minutes.

## The desks (sections on the page)
- **Top Stories** — Hacker News front page (official Firebase API)
- **Release Radar** — latest GitHub releases from watched projects
  (Spring Boot, Kubernetes, Node.js, VS Code, Rust, Go — edit `WATCHED_REPOS` in index.html)
- **Trending on GitHub** — repos created in the last 7 days, ranked by stars (GitHub Search API)
- **Community Pulse** — dev.to top articles of the week (official API)
- **Outage Watch** — live status from GitHub, Cloudflare, npm, Vercel status pages

## Notes & limits
- Unauthenticated GitHub API allows ~60 requests/hour per IP; the page is built to fail
  gracefully per section and retry on refresh.
- Repo is PRIVATE by Bishow's standing rule — the code lives here; publishing the page
  publicly (GitHub Pages needs a public repo on the free plan, or any static host) is a
  separate step taken only when he says so.
- Design/launch plan: CHANNEL_AND_SITE_STRUCTURE.md in the project files; this repo is the
  machine room for the show — rundowns for episodes get drafted from this wire.

## Trust rules (the brand)
Every story links to its primary source. Breaking claims need two sources. Errors are
corrected on the record.
