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

## Live page
- Public mirror repo `thedevdesk` (public, hosting only) serves the page via GitHub Pages:
  https://bishowpratap7.github.io/thedevdesk/
- The hourly scanner commits to this private repo (remote `origin`) and mirrors the same
  commit to the public repo (remote `live`), so the public page stays current.

## Notes & limits
- Unauthenticated GitHub API allows ~60 requests/hour per IP; the page is built to fail
  gracefully per section and retry on refresh.
- This repo is PRIVATE by Bishow's standing rule — the newsroom lives here; only the
  finished page is mirrored to the public hosting repo.
- Design/launch plan: CHANNEL_AND_SITE_STRUCTURE.md in the project files; this repo is the
  machine room for the show — rundowns for episodes get drafted from this wire.

## Trust rules (the brand)
Every story links to its primary source. Breaking claims need two sources. Errors are
corrected on the record.
