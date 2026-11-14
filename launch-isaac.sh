#!/usr/bin/env bash
set -euo pipefail
if pgrep -f '^/isaac-sim/kit/kit ' >/dev/null; then
  echo 'Isaac Sim is already running. Open the browser desktop.'
  exit 0
fi
export DISPLAY=:1 OMNI_KIT_ACCEPT_EULA=YES
cd /isaac-sim
exec ./isaac-sim.sh --allow-root "$@"
