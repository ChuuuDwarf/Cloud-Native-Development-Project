# LIMS devcontainer

Reproducible dev environment that runs **inside a container** and talks to
Postgres + Redis sidecars on a shared Docker network (`lims_devnet`).

Primary target: **Zed**. Also works in VS Code / Cursor.

Ports `8000` (backend) and `3000` (frontend) are published to the host, so
browse `http://localhost:3000` as usual.

For project-level docs (modules, ownership, conventions) see the root
[README.md](../README.md) and [CLAUDE.md](../CLAUDE.md).

---

## TL;DR

```bash
# host
make devcontainer-up               # one-time: create network + start postgres/redis

# Zed → "Connect Dev Container" → accept prompt

# inside the workspace terminal (Zed only — VS Code/Cursor runs this automatically)
bash .devcontainer/post-create.sh  # creates backend/.venv + installs deps
make migrate && make seed          # one-time: schema + dev fixtures

# daily, one process per terminal
make dev-backend                   # uvicorn :8000
make dev-frontend                  # next dev :3000
make worker                        # celery worker (optional)
make beat                          # celery beat   (optional)
```

---

## First-time setup

### 1. Host side (once per machine)

Docker Desktop running, then:

```bash
make devcontainer-up
```

This is idempotent — it creates the `lims_devnet` network if missing, then
brings up Postgres + Redis sidecars in the background.

### 2. Attach the editor

- **Zed**: open the project folder, accept the "Connect Dev Container"
  prompt. (Manual fallback: command palette → "dev: open folder in
  container".)
- **VS Code / Cursor**: command palette → "Dev Containers: Reopen in
  Container".

The first attach takes a few minutes — Docker builds the image
(`python:3.12-slim` + Node 20 + dev CLIs).

### 3. Install project deps (inside the workspace)

```bash
bash .devcontainer/post-create.sh
```

The script is idempotent. It:

- Creates `backend/.venv` (rebuilds it if a stale host venv from a
  different OS is detected).
- `pip install`s `requirements.txt` + `requirements-dev.txt` into the venv.
- `npm ci`s the frontend.

**Zed users must run this manually** — Zed currently doesn't auto-execute
`postCreateCommand`. VS Code / Cursor run it for you.

The venv is auto-activated for every shell because
`.devcontainer/devcontainer.json` puts `backend/.venv/bin` on `PATH`.
You don't need `source .venv/bin/activate`.

### 4. Initialize the database

```bash
make migrate          # alembic upgrade head
make seed             # python scripts/seed_dev.py
```

---

## Daily loop

### Bring the stack up

```bash
# host
make devcontainer-up
```

Then attach with Zed. The post-create step from setup doesn't need to
re-run unless `requirements*.txt` or `package.json` changed.

### Backend — `make dev-backend`

```bash
make dev-backend                      # uvicorn app.main:app --reload :8000
# equivalent to: cd backend && uvicorn app.main:app --reload --port 8000
```

Hits Postgres at `postgres:5432` and Redis at `redis:6379` (resolved via
DNS on `lims_devnet`). Reload-on-save works because the repo is
bind-mounted.

Verify from your host: `curl http://localhost:8000/health` returns 200.

### Frontend — `make dev-frontend`

```bash
make dev-frontend                     # next dev :3000
# equivalent to: cd frontend && npm run dev
```

Open `http://localhost:3000` in your host browser. `NEXT_PUBLIC_API_URL`
is set to `http://localhost:8000/api` for both `next dev` and `next
build`.

### Celery — `make worker` / `make beat`

Optional, only when you're working on `app/workers/` or features that
emit events:

```bash
make worker                           # celery -A app.core.celery_app worker
make beat                             # celery -A app.core.celery_app beat
```

### Migrations — `make revision` / `make migrate`

```bash
make revision msg="add issue priority"   # autogenerate from model changes
make migrate                              # apply pending migrations
```

`alembic` is on `PATH` (it lives in `backend/.venv/bin`).

---

## Build

There's no Python "build" step — the venv is the build artifact, and
post-create.sh handles it.

### Frontend production build

```bash
cd frontend && npm run build
# or
make ci-frontend                      # full CI reproducer (lint + tsc + build + vitest)
```

Output goes to `frontend/.next/`. Next.js is configured with `output:
standalone` (see `frontend/next.config.ts`), so this is what the
production frontend image ships.

### Docker images (host only)

Building the production-style Docker images requires running `docker
compose build` on the **host** (no docker-in-docker inside the
workspace):

```bash
# host
make build                            # docker compose build
make ci-build                         # docker compose build with CI overlay
```

---

## Testing

### Backend (pytest)

```bash
make test-backend                     # pytest --cov=app
# or directly
cd backend && pytest                  # quick run
cd backend && pytest --cov=app        # with coverage
cd backend && pytest tests/path/to/test_x.py::test_y   # single test
```

Tests live in `backend/tests/`. Markers defined in `pyproject.toml`:
`integration` (cross-module), `e2e` (full stack).

### Frontend (vitest)

```bash
make test-frontend                    # npm test
# or
cd frontend && npm test               # vitest run
cd frontend && npx vitest             # watch mode
cd frontend && npm run test:coverage  # with coverage
```

### Lint / format

```bash
make lint                             # backend + frontend
make lint-backend                     # ruff + ruff format --check + mypy
make lint-frontend                    # eslint + tsc --noEmit
make format                           # ruff format + prettier --write
```

### CI reproducers

Run the same steps as `.github/workflows/ci.yml` locally:

```bash
make ci-backend                       # ruff + mypy + alembic + pytest+cov
make ci-frontend                      # eslint + tsc + next build + vitest+cov
```

### E2E (Playwright)

The Playwright suite needs the full Docker stack (backend + celery +
frontend), so it's driven from the **host**, not the devcontainer:

```bash
# host
make ci-e2e                           # boots compose stack + runs Playwright
make ci-down                          # tears it down
```

---

## Useful CLIs available inside the workspace

| Tool | Source |
|---|---|
| `python3`, `pip`, `uvicorn`, `alembic`, `celery`, `pytest`, `ruff`, `mypy` | `backend/.venv/bin` (auto on PATH) |
| `node`, `npm`, `npx` | Node 20 from NodeSource |
| `psql`, `redis-cli` | apt — connect with no args using `PGHOST=postgres`, `PGUSER=lims` etc. (already in `containerEnv`) |
| `make`, `git`, `curl`, `sudo` | apt |

---

## Network model

```
host
 └─ docker network: lims_devnet (external)
     ├─ postgres   (compose service; on lims_devnet AND default)
     ├─ redis      (compose service; on lims_devnet AND default)
     └─ workspace  (this devcontainer; on lims_devnet)
            → reaches sidecars as postgres:5432 / redis:6379
```

Non-devcontainer users running `docker compose up` get the same
behavior — backend / frontend / celery services talk to postgres / redis
on the default compose network. The `make` Docker targets
(`infra`, `up`, `ci-e2e`) all depend on `devcontainer-net`, so they
create the network automatically.

---

## Troubleshooting

- **"network lims_devnet not found"** when compose starts: run
  `make devcontainer-net` on the host. `make devcontainer-up` / `make
  infra` / `make up` do this for you.

- **Zed: `import fastapi could not be resolved` in editor**:
  `backend/.venv` doesn't exist yet, or wasn't built in this container.
  Run `bash .devcontainer/post-create.sh`. Pyright is configured by
  `backend/pyrightconfig.json` to look for `.venv` in `backend/`.

- **`uvicorn` / `alembic` / `pytest` not found**: the venv isn't on
  PATH. Either the post-create script didn't run (run it manually) or
  you're on an older container — Rebuild Container from Zed.

- **Backend can't reach Postgres**: confirm sidecars are up
  (`docker compose ps postgres redis` on host). The devcontainer
  resolves them as `postgres:5432` / `redis:6379` on `lims_devnet`.

- **Sidecars started after the workspace**: if you ran
  `make devcontainer-up` *after* attaching, the workspace may have
  joined `lims_devnet` before postgres/redis did. Restart the workspace
  container (Zed: detach + reattach; VS Code: "Dev Containers: Rebuild
  and Reopen") or just bring sidecars up first next time.

- **macOS host venv leaking in**: the existing `backend/.venv` on a
  macOS host has Mach-O binaries that can't run on Linux.
  `post-create.sh` detects this (`python -c ''` fails) and rebuilds the
  venv as Linux ELF. If you want to keep a host venv for local-dev
  fallback, rename it: `mv backend/.venv backend/venv` on the host.

- **Linux uid mismatch (files owned by uid 1000 on host)**: the
  devcontainer sets `updateRemoteUserUID: true` so VS Code / Cursor
  remap `vscode` to your host uid on attach. Zed doesn't honor this.
  Linux Zed workaround: rebuild image with
  `docker build --build-arg USER_UID=$(id -u) --build-arg USER_GID=$(id -g) \
  -f .devcontainer/Dockerfile -t lims-devcontainer .devcontainer/`.
