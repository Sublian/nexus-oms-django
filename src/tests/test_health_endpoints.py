import pytest
from django.urls import reverse


@pytest.mark.django_db
def test_liveness_returns_ok(client):
    r = client.get(reverse("health-live"))
    assert r.status_code == 200
    assert r.json()["status"] == "ok"


@pytest.mark.django_db
def test_readiness_reports_database_and_redis(client):
    r = client.get(reverse("health-ready"))
    assert r.status_code == 200
    body = r.json()
    assert body["status"] == "ok"
    assert body["checks"]["database"] == "ok"
    assert body["checks"]["redis"] == "ok"
