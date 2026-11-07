"""Rate limiter unit tests and API integration checks."""

import pytest
from fastapi.testclient import TestClient
from starlette.requests import Request

from hepatiq.backend.main import app
from hepatiq.backend.rate_limit import (
    RateLimitSettings,
    SlidingWindowLimiter,
    client_identity,
)
from tests.conftest import REQUIRED_ONLY


@pytest.fixture()
def limited_client(tmp_path, monkeypatch):
    monkeypatch.setenv("HEPATIQ_DB_PATH", str(tmp_path / "history.db"))
    monkeypatch.setenv("HEPATIQ_RATE_LIMIT_REQUESTS", "2")
    monkeypatch.setenv("HEPATIQ_RATE_LIMIT_WINDOW_SECONDS", "60")
    monkeypatch.delenv("HEPATIQ_TRUST_PROXY_HEADERS", raising=False)
    with TestClient(app) as test_client:
        yield test_client


def test_requests_under_limit_succeed(limited_client):
    assert limited_client.post("/predict", json=REQUIRED_ONLY).status_code == 200
    assert limited_client.get("/history").status_code == 200


def test_limit_returns_429_and_retry_after(limited_client):
    assert limited_client.post("/predict", json=REQUIRED_ONLY).status_code == 200
    assert limited_client.post("/predict", json=REQUIRED_ONLY).status_code == 200

    response = limited_client.post("/predict", json=REQUIRED_ONLY)

    assert response.status_code == 429
    assert response.json()["detail"] == "Too many requests; retry later."
    assert int(response.headers["Retry-After"]) >= 1


def test_health_remains_available_after_limit(limited_client):
    limited_client.post("/predict", json=REQUIRED_ONLY)
    limited_client.post("/predict", json=REQUIRED_ONLY)
    assert limited_client.post("/predict", json=REQUIRED_ONLY).status_code == 429

    assert limited_client.get("/health").status_code == 200


def test_identities_have_separate_windows():
    limiter = SlidingWindowLimiter(RateLimitSettings(requests=1, window_seconds=60))

    assert limiter.check("client-a").allowed
    assert not limiter.check("client-a").allowed
    assert limiter.check("client-b").allowed


def test_window_expiry_allows_requests_again():
    now = [100.0]
    limiter = SlidingWindowLimiter(
        RateLimitSettings(requests=1, window_seconds=10),
        clock=lambda: now[0],
    )

    assert limiter.check("client").allowed
    now[0] = 109.9
    denied = limiter.check("client")
    assert not denied.allowed
    assert denied.retry_after_seconds == pytest.approx(0.1)
    now[0] = 110.0
    assert limiter.check("client").allowed


def test_forwarded_for_ignored_without_proxy_trust():
    request = _request(headers=[(b"x-forwarded-for", b"203.0.113.7, 10.0.0.1")])

    assert client_identity(request, trust_proxy_headers=False) == "127.0.0.1"
    assert client_identity(request, trust_proxy_headers=True) == "203.0.113.7"


def test_invalid_env_values_fall_back_to_defaults():
    settings = RateLimitSettings.from_env(
        {
            "HEPATIQ_RATE_LIMIT_REQUESTS": "zero",
            "HEPATIQ_RATE_LIMIT_WINDOW_SECONDS": "-1",
        }
    )

    assert settings.requests == 60
    assert settings.window_seconds == 60.0
    assert settings.trust_proxy_headers is False


def _request(headers):
    return Request(
        {
            "type": "http",
            "http_version": "1.1",
            "method": "GET",
            "scheme": "http",
            "path": "/",
            "raw_path": b"/",
            "query_string": b"",
            "headers": headers,
            "client": ("127.0.0.1", 1234),
            "server": ("testserver", 80),
            "root_path": "",
        }
    )
