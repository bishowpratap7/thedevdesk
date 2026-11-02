#!/bin/bash
# The Dev Desk — hourly wire update: scan feeds, commit + push data/wire.json if it changed.
set -u
cd /home/hatch/workspace/projects/the-dev-desk || exit 1
export GIT_SSH_COMMAND='ssh -i /home/hatch/.ssh/id_ed25519 -o IdentitiesOnly=yes -o StrictHostKeyChecking=accept-new -o UserKnownHostsFile=/home/hatch/.ssh/known_hosts -o ProxyCommand="nc -X connect -x hatch-egress-proxy:3128 %h %p"'
python3 tools/scan.py || exit 1
if git diff --quiet -- data/wire.json && [ -z "$(git status --porcelain -- data/)" ]; then
  echo "WIRE: no changes"
  exit 0
fi
git add data/wire.json
git commit -q -m "Wire update $(date -u +%Y-%m-%dT%H:%MZ)"
git push -q origin main || exit 1
echo "WIRE: updated and pushed"
