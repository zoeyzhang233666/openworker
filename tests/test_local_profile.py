"""Local profile (display name + avatar) — independent of cloud sign-in."""

from __future__ import annotations

import base64

import pytest
from fastapi.testclient import TestClient

from coworker.server import SessionManager, create_app


@pytest.fixture
def client(tmp_path, monkeypatch):
    monkeypatch.setenv("COWORKER_STATE_DIR", str(tmp_path / "state"))
    manager = SessionManager(workspace=tmp_path, data_dir=tmp_path / "data")
    app = create_app(manager)
    with TestClient(app) as c:
        c.manager = manager
        yield c


def _png_bytes() -> bytes:
    # 1×1 PNG
    return base64.b64decode(
        "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mP8z8BQDwAEhQGAhKmMIQAAAABJRU5ErkJggg=="
    )


def test_settings_includes_empty_local_profile(client):
    body = client.get("/v1/settings").json()
    assert body["local_display_name"] == ""
    assert body["local_avatar"] is False


def test_set_and_clear_display_name(client):
    out = client.post(
        "/v1/settings/local-profile", json={"display_name": "  蒋老师  "}
    ).json()
    assert out["ok"]
    assert out["local_display_name"] == "蒋老师"
    assert client.get("/v1/settings").json()["local_display_name"] == "蒋老师"

    cleared = client.post("/v1/settings/local-profile", json={"display_name": "  "}).json()
    assert cleared["ok"]
    assert cleared["local_display_name"] == ""


def test_display_name_rejects_too_long(client):
    body = client.post(
        "/v1/settings/local-profile", json={"display_name": "x" * 41}
    ).json()
    assert not body["ok"]
    assert "too long" in body["error"]


def test_avatar_upload_get_and_delete(client):
    png = _png_bytes()
    up = client.post(
        "/v1/settings/local-profile/avatar",
        json={
            "data_b64": base64.b64encode(png).decode(),
            "content_type": "image/png",
        },
    ).json()
    assert up["ok"]
    assert up["local_avatar"] is True

    got = client.get("/v1/settings/local-profile/avatar")
    assert got.status_code == 200
    assert got.content == png
    assert "image/png" in got.headers.get("content-type", "")

    cleared = client.delete("/v1/settings/local-profile/avatar").json()
    assert cleared["ok"]
    assert cleared["local_avatar"] is False
    assert client.get("/v1/settings/local-profile/avatar").status_code == 404


def test_avatar_rejects_bad_type_and_oversize(client):
    bad = client.post(
        "/v1/settings/local-profile/avatar",
        json={"data_b64": base64.b64encode(b"hello").decode(), "content_type": "text/plain"},
    ).json()
    assert not bad["ok"]

    huge = client.post(
        "/v1/settings/local-profile/avatar",
        json={
            "data_b64": base64.b64encode(b"x" * (2 * 1024 * 1024 + 1)).decode(),
            "content_type": "image/png",
        },
    ).json()
    assert not huge["ok"]
    assert "too large" in huge["error"]


def test_avatar_accepts_data_url_prefix(client):
    png = _png_bytes()
    data_url = "data:image/png;base64," + base64.b64encode(png).decode()
    out = client.post(
        "/v1/settings/local-profile/avatar",
        json={"data_b64": data_url, "content_type": "image/png"},
    ).json()
    assert out["ok"] and out["local_avatar"]
