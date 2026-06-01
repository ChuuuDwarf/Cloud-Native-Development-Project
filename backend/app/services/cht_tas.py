"""Sync HTTP client for the 中華電信 TAS phone callout API.

Sync (not async) because it's only called from the Celery worker, which is a
sync process. Using httpx keeps the surface small and consistent with the
rest of the project.

Auth: ``x-api-key`` header. Base URL + key + service_number all live in
``app.core.config.Settings``; this module is a thin wrapper.

For demo simplicity we only call :meth:`callout` — the service_number is
pre-registered out-of-band (see ``backend/.env``). Receiving call status
(answered / DTMF) requires MQTT and is out of scope for this sprint.

Reference: https://tasapi.cht.com.tw/tas/api/tas_document_api
"""

from __future__ import annotations

import logging
from typing import Any

import httpx

from app.core.config import get_settings

logger = logging.getLogger(__name__)


class CHTTASError(Exception):
    """Raised when the TAS API rejects a request or returns a non-ok status."""


class CHTTASClient:
    """Thin httpx wrapper for the TAS callout endpoint."""

    def __init__(
        self,
        *,
        api_key: str | None = None,
        service_number: str | None = None,
        base_url: str | None = None,
        timeout: float = 10.0,
        enabled: bool | None = None,
    ) -> None:
        settings = get_settings()
        self._api_key = api_key or settings.cht_api_key
        self._service_number = service_number or settings.cht_service_number
        self._base_url = (base_url or settings.cht_base_url).rstrip("/")
        self._timeout = timeout
        # ``tas_enabled`` is the master kill-switch. When False the client
        # short-circuits even if creds happen to be in the env — keeps CI /
        # local dev from accidentally dialling real numbers.
        self._enabled = settings.tas_enabled if enabled is None else enabled

    @property
    def configured(self) -> bool:
        """True only when the master switch is on AND creds are present."""
        return self._enabled and bool(self._api_key) and bool(self._service_number)

    def callout(
        self,
        *,
        phones: list[str],
        text: str,
        welcome_text: str = "中華電信語音通告",
        bye_text: str = "謝謝",
        repeat: int = 2,
        prompt_mode: str = "F",
        ringing_timeout: int = 30,
        tags: list[str] | None = None,
    ) -> dict[str, Any]:
        """Fire a callout. Returns the parsed JSON response on HTTP 200.

        Raises :class:`CHTTASError` if the TAS API responds with status="err"
        or a non-2xx HTTP status, OR if the client isn't configured.
        """
        if not self.configured:
            raise CHTTASError(
                "CHT TAS client is not configured (CHT_API_KEY / CHT_SERVICE_NUMBER unset)"
            )
        if not phones:
            raise CHTTASError("phones list cannot be empty")

        payload = {
            "serviceNumber": self._service_number,
            "phones": phones,
            "ivrData": {
                "welcomeText": welcome_text,
                "text": text,
                "byeText": bye_text,
                "repeat": repeat,
                "promptMode": prompt_mode,
                "node": "MAIN",
            },
            "ringingTimeout": ringing_timeout,
        }
        if tags is not None:
            payload["tags"] = tags

        url = f"{self._base_url}/phone-conn/v1/callout"
        headers = {"x-api-key": self._api_key, "Content-Type": "application/json"}

        try:
            response = httpx.post(url, json=payload, headers=headers, timeout=self._timeout)
        except httpx.HTTPError as exc:
            raise CHTTASError(f"transport error calling TAS: {exc}") from exc

        try:
            body = response.json()
        except ValueError as exc:
            raise CHTTASError(
                f"TAS returned non-JSON body (status={response.status_code}): {response.text!r}"
            ) from exc

        if response.status_code != 200 or body.get("status") != "ok":
            raise CHTTASError(f"TAS callout failed: status={response.status_code} body={body!r}")

        logger.info(
            "cht callout queued: groupId=%s phones=%s",
            body.get("groupId"),
            phones,
        )
        return body
