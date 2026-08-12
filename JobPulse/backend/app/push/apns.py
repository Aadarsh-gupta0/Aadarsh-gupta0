"""Token-based APNs client (HTTP/2, JWT ES256)."""

from __future__ import annotations

import json
import logging
import time
from dataclasses import dataclass
from typing import Any

import httpx
import jwt

from ..config import Settings, get_settings

log = logging.getLogger(__name__)

# Apple rejects provider tokens older than 1h; refresh comfortably inside that.
TOKEN_TTL_SECONDS = 45 * 60

# Responses that mean "this device token is dead, stop using it".
DEAD_TOKEN_REASONS = {"BadDeviceToken", "Unregistered", "DeviceTokenNotForTopic"}


@dataclass
class PushResult:
    ok: bool
    status_code: int | None = None
    apns_id: str | None = None
    reason: str | None = None

    @property
    def token_is_dead(self) -> bool:
        return self.reason in DEAD_TOKEN_REASONS


class APNsClient:
    """Sends alerts to Apple. Safe to keep for the lifetime of the process."""

    def __init__(self, settings: Settings | None = None) -> None:
        self.settings = settings or get_settings()
        self._client: httpx.AsyncClient | None = None
        self._token: str | None = None
        self._token_issued_at: float = 0.0

    # --- lifecycle -----------------------------------------------------

    @property
    def configured(self) -> bool:
        return self.settings.apns_configured

    async def __aenter__(self) -> APNsClient:
        return self

    async def __aexit__(self, *_exc: object) -> None:
        await self.aclose()

    def _http(self) -> httpx.AsyncClient:
        if self._client is None:
            self._client = httpx.AsyncClient(
                http2=True,
                base_url=f"https://{self.settings.apns_host}",
                timeout=15.0,
            )
        return self._client

    async def aclose(self) -> None:
        if self._client is not None:
            await self._client.aclose()
            self._client = None

    # --- auth ----------------------------------------------------------

    def _provider_token(self) -> str:
        now = time.time()
        if self._token and (now - self._token_issued_at) < TOKEN_TTL_SECONDS:
            return self._token

        self._token = jwt.encode(
            {"iss": self.settings.apns_team_id, "iat": int(now)},
            self.settings.read_apns_key(),
            algorithm="ES256",
            headers={"alg": "ES256", "kid": self.settings.apns_key_id},
        )
        self._token_issued_at = now
        return self._token

    # --- sending -------------------------------------------------------

    async def send(
        self,
        device_token: str,
        payload: dict[str, Any],
        *,
        collapse_id: str | None = None,
        priority: int = 10,
        expiration: int | None = None,
    ) -> PushResult:
        if not self.configured:
            log.info("APNs not configured — would have sent to %s…", device_token[:8])
            return PushResult(ok=False, reason="NotConfigured")

        headers = {
            "authorization": f"bearer {self._provider_token()}",
            "apns-topic": self.settings.apns_topic,
            "apns-push-type": "alert",
            "apns-priority": str(priority),
            "content-type": "application/json",
        }
        if collapse_id:
            headers["apns-collapse-id"] = collapse_id[:64]
        if expiration is not None:
            headers["apns-expiration"] = str(expiration)

        try:
            response = await self._http().post(
                f"/3/device/{device_token}",
                content=json.dumps(payload).encode(),
                headers=headers,
            )
        except httpx.HTTPError as exc:
            log.warning("APNs transport error: %s", exc)
            return PushResult(ok=False, reason=f"Transport:{type(exc).__name__}")

        apns_id = response.headers.get("apns-id")
        if response.status_code == 200:
            return PushResult(ok=True, status_code=200, apns_id=apns_id)

        reason = None
        try:
            reason = response.json().get("reason")
        except ValueError:
            reason = response.text[:120] or None

        # 403 with ExpiredProviderToken: drop the cached JWT so the next call re-mints.
        if reason == "ExpiredProviderToken":
            self._token = None

        log.warning("APNs %s for %s… → %s", response.status_code, device_token[:8], reason)
        return PushResult(
            ok=False, status_code=response.status_code, apns_id=apns_id, reason=reason
        )
