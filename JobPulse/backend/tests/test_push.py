"""APNs payload shape and provider-token handling."""

from __future__ import annotations

import jwt
import pytest
from conftest import make_job
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import ec

from app.config import Settings
from app.db import session_scope
from app.models import Job
from app.push import APNsClient, build_payload, collapse_id_for, thread_id_for


@pytest.fixture
def job():
    """Yielded from inside an open session so relationships stay loadable."""
    job_id = make_job("Senior Flutter Engineer", "Google", location="Remote", remote_hint=True)
    with session_scope() as db:
        yield db.get(Job, job_id)


class TestPayload:
    def test_alert_uses_company_as_title(self, job):
        alert = build_payload(job, profile_slug="flutter", score=0.9)["aps"]["alert"]
        assert alert["title"] == "Google"
        assert alert["subtitle"] == "Senior Flutter Engineer"
        assert alert["body"]

    def test_thread_id_groups_by_company(self, job):
        payload = build_payload(job, profile_slug="flutter", score=0.9)
        assert payload["aps"]["thread-id"] == "company-google"

    def test_collapse_id_is_per_job(self, job):
        assert collapse_id_for(job) == f"job-{job.id}"

    def test_two_roles_at_one_company_share_a_thread(self):
        ids = []
        for i, title in enumerate(["Flutter Engineer", "Product Designer"]):
            job_id = make_job(
                title, "Google", source_id=str(i), description="Flutter and product design."
            )
            with session_scope() as db:
                ids.append(thread_id_for(db.get(Job, job_id)))
        assert len(set(ids)) == 1

    def test_mutable_content_enables_the_service_extension(self, job):
        assert build_payload(job, profile_slug="flutter", score=0.5)["aps"]["mutable-content"] == 1

    def test_relevance_score_is_clamped(self, job):
        assert (
            build_payload(job, profile_slug="flutter", score=4.2)["aps"]["relevance-score"] == 1.0
        )
        assert build_payload(job, profile_slug="flutter", score=-1)["aps"]["relevance-score"] == 0.0

    def test_badge_is_optional(self, job):
        assert "badge" not in build_payload(job, profile_slug="flutter", score=0.5)["aps"]
        assert build_payload(job, profile_slug="flutter", score=0.5, badge=7)["aps"]["badge"] == 7

    def test_custom_keys_carry_deep_link_and_context(self, job):
        payload = build_payload(
            job, profile_slug="flutter", score=0.82, matched_terms=["Flutter", "Dart"]
        )
        assert payload["deepLink"] == f"jobpulse://job/{job.id}"
        assert payload["jobId"] == job.id
        assert payload["profileLabel"] == "Flutter Dev"
        assert payload["accent"].startswith("#")
        assert payload["matchedTerms"] == ["Flutter", "Dart"]
        assert payload["isRemote"] is True

    def test_matched_terms_are_capped(self, job):
        payload = build_payload(
            job, profile_slug="flutter", score=0.5, matched_terms=[f"t{i}" for i in range(20)]
        )
        assert len(payload["matchedTerms"]) == 6

    def test_body_falls_back_to_matched_terms(self, job):
        job.description_text = ""
        payload = build_payload(
            job, profile_slug="flutter", score=0.5, matched_terms=["Flutter", "Dart"]
        )
        assert payload["aps"]["alert"]["body"] == "Matches Flutter, Dart"

    def test_unknown_profile_still_produces_a_payload(self, job):
        payload = build_payload(job, profile_slug="mystery", score=0.5)
        assert payload["profileLabel"] == "mystery"
        assert payload["accent"] == "#7C8CFF"


def _p8_key() -> str:
    """A throwaway P-256 key in the same PEM shape as an Apple .p8."""
    key = ec.generate_private_key(ec.SECP256R1())
    return key.private_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PrivateFormat.PKCS8,
        encryption_algorithm=serialization.NoEncryption(),
    ).decode()


class TestAPNsClient:
    def test_reports_unconfigured(self):
        assert APNsClient(Settings(apns_team_id=None)).configured is False

    async def test_send_without_config_is_a_no_op(self):
        client = APNsClient(Settings(apns_team_id=None))
        result = await client.send("token", {"aps": {}})
        assert result.ok is False
        assert result.reason == "NotConfigured"

    def test_configured_when_all_parts_present(self):
        settings = Settings(
            apns_team_id="TEAM123456", apns_key_id="KEY1234567", apns_auth_key=_p8_key()
        )
        assert settings.apns_configured is True

    def test_provider_token_is_signed_es256_with_kid(self):
        settings = Settings(
            apns_team_id="TEAM123456", apns_key_id="KEY1234567", apns_auth_key=_p8_key()
        )
        token = APNsClient(settings)._provider_token()

        header = jwt.get_unverified_header(token)
        assert header["alg"] == "ES256"
        assert header["kid"] == "KEY1234567"

        claims = jwt.decode(token, options={"verify_signature": False})
        assert claims["iss"] == "TEAM123456"
        assert "iat" in claims

    def test_provider_token_is_cached(self):
        settings = Settings(
            apns_team_id="TEAM123456", apns_key_id="KEY1234567", apns_auth_key=_p8_key()
        )
        client = APNsClient(settings)
        assert client._provider_token() == client._provider_token()

    def test_sandbox_and_production_hosts(self):
        assert Settings(apns_use_sandbox=True).apns_host == "api.sandbox.push.apple.com"
        assert Settings(apns_use_sandbox=False).apns_host == "api.push.apple.com"

    def test_dead_token_reasons(self):
        from app.push.apns import PushResult

        assert PushResult(ok=False, reason="Unregistered").token_is_dead is True
        assert PushResult(ok=False, reason="BadDeviceToken").token_is_dead is True
        assert PushResult(ok=False, reason="PayloadTooLarge").token_is_dead is False
