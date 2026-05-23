from __future__ import annotations

from fastapi import APIRouter

router = APIRouter(prefix="/api", tags=["Users"])

# Deprecated: /api/me is implemented by app.modules.auth.router and is mounted
# from the real authentication system. This router intentionally exposes no
# mock user endpoint.
