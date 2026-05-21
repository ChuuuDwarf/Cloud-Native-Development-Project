# LIMS devcontainer image.
#
# Single-image dev environment for the unified-workspace topology:
#   - Python 3.12 (matches backend/dockerfile)
#   - Node 20  (matches frontend/dockerfile)
#   - Postgres + Redis CLIs for debugging the sidecar services
#   - GNU make (the team's command surface)
#
# Dependencies (pip / npm) are deliberately NOT installed here. They are
# installed by .devcontainer/post-create.sh once the repo is bind-mounted,
# so they always match requirements*.txt / package.json on disk and survive
# `git checkout` between branches with different deps.

FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    DEBIAN_FRONTEND=noninteractive

# System packages:
#   build-essential, libpq-dev — needed by asyncpg / psycopg / bcrypt wheels
#   curl, ca-certificates, gnupg — required to bootstrap the NodeSource repo
#   git              — devcontainers expect git inside the workspace
#   postgresql-client, redis-tools — psql / redis-cli for poking at sidecars
#   make             — the project's Makefile is the canonical command surface
#   sudo             — non-root user occasionally needs to apt-get install one-offs
RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        build-essential \
        libpq-dev \
        curl \
        git \
        ca-certificates \
        gnupg \
        postgresql-client \
        redis-tools \
        make \
        sudo \
    && rm -rf /var/lib/apt/lists/*

# Node 20 via NodeSource — same major as frontend/dockerfile.
RUN curl -fsSL https://deb.nodesource.com/setup_20.x | bash - \
    && apt-get install -y --no-install-recommends nodejs \
    && rm -rf /var/lib/apt/lists/*

# Non-root user that matches the devcontainer convention (uid 1000).
# Passwordless sudo so the user can `apt-get install` ad-hoc tools without
# rebuilding the image.
ARG USERNAME=vscode
ARG USER_UID=1000
ARG USER_GID=1000
RUN groupadd --gid ${USER_GID} ${USERNAME} \
    && useradd --uid ${USER_UID} --gid ${USER_GID} --create-home --shell /bin/bash ${USERNAME} \
    && echo "${USERNAME} ALL=(root) NOPASSWD:ALL" > /etc/sudoers.d/${USERNAME} \
    && chmod 0440 /etc/sudoers.d/${USERNAME}

WORKDIR /workspaces/lims

# Put the project's Python venv FIRST on PATH so uvicorn / alembic / pytest /
# ruff / mypy "just work" once post-create.sh has created backend/.venv. Done
# here (not in devcontainer.json containerEnv) because Zed's devcontainer
# driver doesn't resolve the `${containerEnv:PATH}` spec substitution -- it
# leaks the literal string into the UID-update Dockerfile and breaks the
# build with "unsupported modifier (:P)". Dockerfile sees a real ${PATH}.
ENV PATH="/workspaces/lims/backend/.venv/bin:${PATH}"

USER ${USERNAME}
