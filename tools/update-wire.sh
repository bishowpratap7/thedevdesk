#!/bin/bash
# The Dev Desk — hourly wire update: scan feeds, commit + push data/wire.json if it changed.
set -u
cd /home/hatch/workspace/projects/the-dev-desk || exit 1
export GIT_SSH_COMMAND='ssh -i /home/hatch/.ssh/id_ed25519 -o IdentitiesOnly=yes -o StrictHostKeyChecking=accept-new -o UserKnownHostsFile=/home/hatch/.ssh/known_hosts -o ProxyCommand="nc -X connect -x hatch-egress-proxy:3128 %h %p"'
python3 tools/scan.py || exit 1
if [ -z "$(git status --porcelain -- data/ index.html feed.xml sitemap.xml)" ]; then
  echo "WIRE: no changes"
  exit 0
fi
git add data/wire.json index.html feed.xml sitemap.xml
git commit -q -m "Wire update $(date -u +%Y-%m-%dT%H:%MZ)"
git push -q origin main || exit 1
git push -q live main || echo "WIRE: warning — live mirror push failed"
echo "WIRE: updated and pushed"

# IndexNow ping (Bing/Yandex/etc.) — tells search engines the page just changed.
# The key file lives at the site root; failure here never fails the update.
KEYFILE=$(ls [0-9a-f]*.txt 2>/dev/null | grep -v robots | head -1)
if [ -n "$KEYFILE" ]; then
  KEY="$(cat $KEYFILE)"
  curl -s --max-time 15 "https://api.indexnow.org/indexnow?url=https%3A%2F%2Fbishowpratap7.github.io%2Fthedevdesk%2F&key=$KEY" >/dev/null 2>&1 || true
  echo "WIRE: IndexNow pinged"
fi
