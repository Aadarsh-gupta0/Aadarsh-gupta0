"""HTTP contract — this is exactly what the iOS app decodes."""

from __future__ import annotations

import pytest
from conftest import make_job

TOKEN = "b" * 64


@pytest.fixture
def registered(client):
    response = client.post(
        "/v1/devices",
        json={
            "apnsToken": TOKEN,
            "displayName": "Aadarsh",
            "interests": ["flutter", "ui_ux", "product_design"],
            "timezone": "Asia/Kolkata",
        },
    )
    assert response.status_code == 201
    return response.json()


class TestMeta:
    def test_healthz(self, client):
        body = client.get("/healthz").json()
        assert body["status"] == "ok"
        assert "apnsConfigured" in body

    def test_interest_catalogue(self, client):
        body = client.get("/v1/interests").json()
        slugs = {item["slug"] for item in body}
        assert {"flutter", "ui_ux", "product_design"}.issubset(slugs)
        assert all(item["accent"].startswith("#") for item in body)


class TestFeed:
    def test_returns_camel_case_payload(self, client):
        make_job("Senior Flutter Engineer", "Acme")
        item = client.get("/v1/feed").json()["items"][0]
        assert item["isRemote"] is False
        assert item["topScore"] > 0
        assert item["company"]["name"] == "Acme"
        assert item["matches"][0]["profileSlug"] == "flutter"

    def test_filters_by_interest(self, client):
        make_job("Senior Flutter Engineer", "Acme")
        assert (
            client.get("/v1/feed", params={"interests": ["product_design"]}).json()["items"] == []
        )

    def test_internships_filter(self, client):
        make_job("Flutter Developer", "Acme", source_id="1")
        make_job(
            "Flutter Development Intern",
            "Beta",
            source_id="2",
            description="A 6 month internship with Flutter and Dart.",
        )
        items = client.get("/v1/feed", params={"filter": "internships"}).json()["items"]
        assert items and all(i["isInternship"] for i in items)

    def test_remote_filter(self, client):
        make_job("Flutter Developer", "Acme", source_id="1", location="Bengaluru, India")
        make_job("Flutter Engineer", "Beta", source_id="2", location="Remote", remote_hint=True)
        items = client.get("/v1/feed", params={"filter": "remote"}).json()["items"]
        assert items and all(i["isRemote"] for i in items)

    def test_popular_orders_by_score(self, client):
        make_job(
            "Software Engineer", "Weak", source_id="1", description="We sometimes touch Flutter."
        )
        make_job("Senior Flutter Engineer", "Strong", source_id="2")
        items = client.get("/v1/feed", params={"filter": "popular"}).json()["items"]
        scores = [i["topScore"] for i in items]
        assert scores == sorted(scores, reverse=True)

    def test_new_filter_uses_recency_window(self, client):
        from datetime import UTC, datetime, timedelta

        from app.db import session_scope
        from app.models import Job

        job_id = make_job("Senior Flutter Engineer", "Acme")
        with session_scope() as db:
            db.get(Job, job_id).posted_at = datetime.now(UTC) - timedelta(days=7)

        assert client.get("/v1/feed", params={"filter": "new"}).json()["items"] == []
        assert client.get("/v1/feed", params={"filter": "all"}).json()["items"]

    def test_text_query(self, client):
        make_job("Senior Flutter Engineer", "Acme", source_id="1")
        make_job(
            "Product Designer",
            "Northwind",
            source_id="2",
            description="End-to-end product design in Figma.",
        )
        items = client.get("/v1/feed", params={"query": "Northwind"}).json()["items"]
        assert [i["company"]["name"] for i in items] == ["Northwind"]

    def test_pagination_cursor(self, client):
        for i in range(5):
            make_job(f"Flutter Engineer {i}", f"Company {i}", source_id=str(i))

        first = client.get("/v1/feed", params={"limit": 2}).json()
        assert len(first["items"]) == 2
        assert first["total"] == 5
        assert first["nextCursor"] == "2"

        second = client.get("/v1/feed", params={"limit": 2, "cursor": first["nextCursor"]}).json()
        assert {i["id"] for i in first["items"]}.isdisjoint({i["id"] for i in second["items"]})

    def test_last_page_has_no_cursor(self, client):
        make_job("Flutter Developer", "Acme")
        assert client.get("/v1/feed", params={"limit": 10}).json()["nextCursor"] is None

    def test_min_score_gate(self, client):
        make_job(
            "Software Engineer",
            "Acme",
            description="Our Android app has some Flutter screens.",
        )
        items = client.get("/v1/feed", params={"minScore": 0.0}).json()["items"]
        assert items, "job should be visible with the gate wide open"

        above = min(1.0, items[0]["topScore"] + 0.05)
        assert client.get("/v1/feed", params={"minScore": above}).json()["items"] == []

    def test_bad_cursor_is_tolerated(self, client):
        make_job("Flutter Developer", "Acme")
        assert client.get("/v1/feed", params={"cursor": "junk"}).status_code == 200


class TestStackedFeed:
    def test_groups_by_company(self, client):
        make_job("Flutter Engineer", "Google", source_id="1")
        make_job("Flutter Architect", "Google", source_id="2")
        make_job(
            "Product Designer", "Figma", source_id="3", description="End-to-end product design."
        )

        stacks = client.get("/v1/feed/stacked").json()["stacks"]
        by_company = {s["company"]["name"]: s for s in stacks}
        assert len(by_company["Google"]["jobs"]) == 2
        assert len(by_company["Figma"]["jobs"]) == 1

    def test_per_company_cap(self, client):
        for i in range(6):
            make_job(f"Flutter Engineer {i}", "Google", source_id=str(i))
        stacks = client.get("/v1/feed/stacked", params={"perCompany": 3}).json()["stacks"]
        assert len(stacks[0]["jobs"]) == 3

    def test_reports_top_score(self, client):
        make_job("Senior Flutter Engineer", "Google")
        assert client.get("/v1/feed/stacked").json()["stacks"][0]["topScore"] > 0


class TestJobDetail:
    def test_returns_description_and_company(self, client):
        job_id = make_job("Senior Flutter Engineer", "Acme")
        body = client.get(f"/v1/jobs/{job_id}").json()
        assert body["descriptionText"]
        assert body["companyDetail"]["slug"] == "acme"
        assert body["applyUrl"].startswith("https://")

    def test_related_roles_at_the_same_company(self, client):
        first = make_job("Flutter Engineer", "Google", source_id="1")
        make_job("Flutter Architect", "Google", source_id="2")
        related = client.get(f"/v1/jobs/{first}").json()["related"]
        assert [r["title"] for r in related] == ["Flutter Architect"]

    def test_missing_job_is_404(self, client):
        assert client.get("/v1/jobs/999999").status_code == 404

    def test_company_endpoint(self, client):
        make_job("Flutter Engineer", "Google")
        body = client.get("/v1/companies/google").json()
        assert body["name"] == "Google"
        assert body["openRoles"] == 1

    def test_missing_company_is_404(self, client):
        assert client.get("/v1/companies/nope").status_code == 404


class TestDevices:
    def test_registration_is_idempotent(self, client, registered):
        again = client.post(
            "/v1/devices",
            json={"apnsToken": TOKEN, "interests": ["flutter"]},
        )
        assert again.status_code == 201
        assert again.json()["id"] == registered["id"]

    def test_unknown_interests_are_dropped(self, client):
        body = client.post(
            "/v1/devices",
            json={"apnsToken": "c" * 64, "interests": ["flutter", "underwater-basket-weaving"]},
        ).json()
        assert body["interests"] == ["flutter"]

    def test_short_token_is_rejected(self, client):
        assert client.post("/v1/devices", json={"apnsToken": "short"}).status_code == 422

    def test_read_and_patch(self, client, registered):
        assert client.get(f"/v1/devices/{TOKEN}").json()["displayName"] == "Aadarsh"

        patched = client.patch(
            f"/v1/devices/{TOKEN}",
            json={"pushEnabled": False, "internshipsOnly": True, "minScore": 0.8},
        ).json()
        assert patched["pushEnabled"] is False
        assert patched["internshipsOnly"] is True
        assert patched["minScore"] == 0.8

    def test_patch_leaves_unset_fields_alone(self, client, registered):
        patched = client.patch(f"/v1/devices/{TOKEN}", json={"minScore": 0.7}).json()
        assert patched["displayName"] == "Aadarsh"
        assert patched["interests"] == ["flutter", "ui_ux", "product_design"]

    def test_unknown_device_is_404(self, client):
        assert client.get("/v1/devices/" + "z" * 64).status_code == 404

    def test_delete_deactivates(self, client, registered):
        assert client.delete(f"/v1/devices/{TOKEN}").status_code == 204
        assert client.get(f"/v1/devices/{TOKEN}").json()["pushEnabled"] is False


class TestSavedJobs:
    def test_save_list_and_remove(self, client, registered):
        job_id = make_job("Senior Flutter Engineer", "Acme")

        created = client.post(f"/v1/devices/{TOKEN}/saved", json={"jobId": job_id})
        assert created.status_code == 201
        assert created.json()["job"]["id"] == job_id

        listed = client.get(f"/v1/devices/{TOKEN}/saved").json()
        assert len(listed) == 1

        assert client.delete(f"/v1/devices/{TOKEN}/saved/{job_id}").status_code == 204
        assert client.get(f"/v1/devices/{TOKEN}/saved").json() == []

    def test_saving_twice_updates_in_place(self, client, registered):
        job_id = make_job("Senior Flutter Engineer", "Acme")
        client.post(f"/v1/devices/{TOKEN}/saved", json={"jobId": job_id})
        client.post(f"/v1/devices/{TOKEN}/saved", json={"jobId": job_id, "state": "applied"})

        listed = client.get(f"/v1/devices/{TOKEN}/saved").json()
        assert len(listed) == 1
        assert listed[0]["state"] == "applied"

    def test_dismissed_jobs_are_hidden(self, client, registered):
        job_id = make_job("Senior Flutter Engineer", "Acme")
        client.post(f"/v1/devices/{TOKEN}/saved", json={"jobId": job_id, "state": "dismissed"})
        assert client.get(f"/v1/devices/{TOKEN}/saved").json() == []

    def test_saving_a_missing_job_is_404(self, client, registered):
        assert client.post(f"/v1/devices/{TOKEN}/saved", json={"jobId": 999999}).status_code == 404


class TestAdmin:
    def test_test_push_without_apns_is_503(self, client):
        make_job("Flutter Developer", "Acme")
        response = client.post("/v1/admin/test-push", json={"apnsToken": TOKEN})
        assert response.status_code == 503
