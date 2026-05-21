#!/usr/bin/env bash
# Idempotent first-attach setup for the LIMS devcontainer.
#
# Runs as the non-root `vscode` user with the repo bind-mounted at
# /workspaces/lims. Safe to re-run by hand from a workspace terminal.
#
# Zed note: at the time of writing Zed does not auto-execute
# postCreateCommand, so the README tells the user to run this manually
# after the workspace attaches. VS Code / Cursor will run it for them.

set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "${REPO_ROOT}"

VENV="${REPO_ROOT}/backend/.venv"

# If the venv exists but was built on a different OS (e.g. macOS host venv
# bind-mounted into this Linux container), the python binary won't be a
# Linux ELF. Detect and rebuild.
needs_rebuild=0
if [ ! -x "${VENV}/bin/python" ]; then
    needs_rebuild=1
elif ! "${VENV}/bin/python" -c '' >/dev/null 2>&1; then
    echo "==> Existing backend/.venv isn't usable in this container (likely a host venv from another OS); recreating"
    needs_rebuild=1
fi

if [ "${needs_rebuild}" = "1" ]; then
    rm -rf "${VENV}"
    python3 -m venv "${VENV}"
fi

echo "==> Installing backend Python deps into ${VENV}"
"${VENV}/bin/pip" install --upgrade pip
"${VENV}/bin/pip" install \
    -r backend/requirements.txt \
    -r backend/requirements-dev.txt

echo "==> Installing frontend Node deps"
(cd frontend && npm ci)

cat <<'EOF'

Devcontainer setup complete.

Next steps (run on the host once, then inside the workspace terminal):

  Host:        make devcontainer-up     # brings up postgres + redis sidecars
  Workspace:   make migrate && make seed
  Workspace:   make dev-backend         # in one terminal
  Workspace:   make dev-frontend        # in another
  Workspace:   make worker              # optional, for Celery tasks
  Workspace:   make beat                # optional, for scheduled jobs

EOF
