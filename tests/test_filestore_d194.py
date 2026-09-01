"""D-194 FileStorage / COS delivery contracts (no live Tencent network)."""

from __future__ import annotations

from pathlib import Path

import pytest

from coworker.connectors.file_delivery import deliver_file, format_cos_url_message
from coworker.connectors.tools import make_send_file_tool
from coworker.filestore import (
    FILESTORE_SECRET_PROFILE,
    MemoryFileStorage,
    NullFileStorage,
    load_file_storage,
)
from coworker.filestore.config import CosConfig, validate_public_config
from coworker.filestore.paths import build_object_key, validate_upload_bytes
from coworker.filestore.tencent_cos import TencentCosStorage
from coworker.secrets import SecretStore


def test_memory_storage_builds_public_url_and_chinese_name():
    store = MemoryFileStorage(
        pub_url="https://chemcloud-1304660855.cos.ap-shanghai.myqcloud.com/",
        folder="chemclaw",
    )
    ref = store.upload(b"%PDF-1.4 hello", filename="报价单.pdf", content_type="application/pdf")
    assert ref.filename == "报价单.pdf"
    assert ref.key.startswith("chemclaw/")
    assert ref.url.startswith(
        "https://chemcloud-1304660855.cos.ap-shanghai.myqcloud.com/chemclaw/"
    )
    assert store.exists(ref)
    assert ref.sha256
    assert "%E6%8A%A5%E4%BB%B7%E5%8D%95.pdf" in ref.url
    assert store.download(ref) == b"%PDF-1.4 hello"


def test_cos_public_config_requires_safe_https_values():
    assert validate_public_config("bucket-123", "ap-shanghai", "http://bad.test/", "x")
    assert validate_public_config("bucket-123", "ap-shanghai", "https://u:p@bad.test/", "x")
    assert validate_public_config("bucket-123", "ap-shanghai", "https://ok.test/", "../x")
    assert validate_public_config("bucket-123", "ap-shanghai", "https://ok.test/", "safe") is None


def test_tencent_cos_fake_client_upload_download_and_integrity():
    config = CosConfig(
        secret_id="AKID-test",
        secret_key="secret-test",
        bucket="bucket-123",
        region="ap-shanghai",
        pub_url="https://bucket-123.cos.ap-shanghai.myqcloud.com/",
        folder="chemclaw-test",
    )

    class Body:
        def __init__(self, data):
            self.data = data

        def get_raw_stream(self):
            return self

        def read(self, limit=-1):
            return self.data if limit < 0 else self.data[:limit]

    class FakeClient:
        def __init__(self):
            self.objects = {}
            self.last_put = None

        def put_object(self, **kwargs):
            self.last_put = kwargs
            self.objects[kwargs["Key"]] = kwargs["Body"]

        def get_object(self, **kwargs):
            return {"Body": Body(self.objects[kwargs["Key"]])}

        def object_exists(self, **kwargs):
            return kwargs["Key"] in self.objects

    store = TencentCosStorage(config)
    fake = FakeClient()
    store._client = fake
    ref = store.upload(b"a,b\n1,2", filename="数据.csv", content_type="text/csv")
    assert fake.last_put["EnableMD5"] is True
    assert fake.last_put["Metadata"]["sha256"] == ref.sha256
    assert "filename*=UTF-8''" in fake.last_put["ContentDisposition"]
    assert fake.last_put["ContentDisposition"].startswith("attachment")
    assert store.exists(ref)
    assert store.download(ref) == b"a,b\n1,2"


def test_tencent_cos_html_upload_uses_inline_disposition():
    """D-195: report HTML must open in browser, not force download."""
    config = CosConfig(
        secret_id="AKID-test",
        secret_key="secret-test",
        bucket="bucket-123",
        region="ap-shanghai",
        pub_url="https://bucket-123.cos.ap-shanghai.myqcloud.com/",
        folder="chemclaw-test",
    )

    class FakeClient:
        def __init__(self):
            self.last_put = None

        def put_object(self, **kwargs):
            self.last_put = kwargs

    store = TencentCosStorage(config)
    fake = FakeClient()
    store._client = fake
    store.upload(
        b"<!DOCTYPE html><html></html>",
        filename="报告.html",
        content_type="text/html; charset=utf-8",
    )
    assert fake.last_put["ContentDisposition"].startswith("inline")
    assert fake.last_put["ContentType"].startswith("text/html")


def test_validate_rejects_bad_extension_and_empty():
    with pytest.raises(Exception):
        validate_upload_bytes(b"abc", "x.exe")
    with pytest.raises(Exception):
        validate_upload_bytes(b"", "a.pdf")


def test_object_key_rejects_folder_traversal_segments():
    key = build_object_key("../evil", "a.pdf", unique="abc")
    assert ".." not in key
    assert key.endswith("_a.pdf")
    assert "/evil/" in f"/{key}" or key.startswith("evil/")


def test_null_storage_errors_in_chinese():
    null = NullFileStorage()
    assert not null.configured()
    with pytest.raises(Exception) as exc:
        null.upload(b"x", filename="a.pdf")
    assert "未配置" in str(exc.value)


def test_load_file_storage_from_secrets_and_prefs(tmp_path: Path):
    secrets = SecretStore(tmp_path / "secrets.json")
    assert isinstance(load_file_storage(secrets, {}), NullFileStorage)
    secrets.put(
        FILESTORE_SECRET_PROFILE,
        {"type": "filestore", "secret_id": "AKIDtest", "secret_key": "secret"},
    )
    prefs = {
        "filestore_cos": {
            "enabled": True,
            "bucket": "chemcloud-1304660855",
            "region": "ap-shanghai",
            "pub_url": "https://chemcloud-1304660855.cos.ap-shanghai.myqcloud.com/",
            "folder": "chemclaw",
        }
    }
    storage = load_file_storage(secrets, prefs)
    assert storage.configured()
    assert storage.storage_id == "tencent-cos"


def test_telegram_send_file_uses_cos_url(tmp_path: Path):
    secrets = SecretStore(tmp_path / "s.json")
    secrets.put("telegram:default", {"bot_token": "tg-token", "allowed_users": ["*"]})
    ws = tmp_path / "ws"
    ws.mkdir()
    (ws / "note.pdf").write_bytes(b"%PDF-1.4 data")
    sent: list[tuple] = []

    def text_sender(token, chat_id, text, thread_id=None):
        from coworker.connectors.base import SendResult

        sent.append((token, chat_id, text, thread_id))
        return SendResult(True, message_id="m1")

    store = MemoryFileStorage()
    tool = make_send_file_tool(
        secrets,
        workspace=ws,
        file_senders={},  # telegram has no native file sender
        text_senders={"telegram": text_sender},
        file_storage=store,
    )
    out = tool(target="telegram:12345", path="note.pdf", title="报告")
    assert out.get("ok") is True
    assert out.get("delivery") == "cos_url"
    assert out["file_ref"]["url"]
    assert "https://example.test/" in sent[0][2] or "chemclaw/" in sent[0][2]
    assert "报告" in sent[0][2] or "note.pdf" in sent[0][2]


def test_telegram_without_cos_returns_actionable_error(tmp_path: Path):
    secrets = SecretStore(tmp_path / "s.json")
    secrets.put("telegram:default", {"bot_token": "tg-token", "allowed_users": ["*"]})
    ws = tmp_path / "ws"
    ws.mkdir()
    (ws / "note.pdf").write_bytes(b"%PDF-1.4 data")

    def text_sender(token, chat_id, text, thread_id=None):
        from coworker.connectors.base import SendResult

        return SendResult(True, message_id="m1")

    tool = make_send_file_tool(
        secrets,
        workspace=ws,
        file_senders={},
        text_senders={"telegram": text_sender},
        file_storage=NullFileStorage(),
    )
    out = tool(target="telegram:12345", path="note.pdf")
    assert "error" in out
    assert "COS" in out["error"] or "云" in out["error"]


def test_slack_native_preferred_even_with_cos(tmp_path: Path):
    secrets = SecretStore(tmp_path / "s.json")
    secrets.put("slack:default", {"bot_token": "xoxb-test", "allowed_users": ["*"]})
    ws = tmp_path / "ws"
    ws.mkdir()
    (ws / "note.pdf").write_bytes(b"%PDF-1.4 data")
    native_calls: list = []

    def file_sender(token, chat_id, thread_id, filename, data, title=None, comment=None):
        from coworker.connectors.base import SendResult

        native_calls.append(filename)
        return SendResult(True, message_id="F123")

    store = MemoryFileStorage()
    tool = make_send_file_tool(
        secrets,
        workspace=ws,
        file_senders={"slack": file_sender},
        text_senders={},
        file_storage=store,
    )
    out = tool(target="slack:C0123", path="note.pdf")
    assert out.get("ok") is True
    assert out.get("delivery") == "native"
    assert native_calls == ["note.pdf"]
    assert out.get("file_ref")  # also uploaded for cross-terminal ref


def test_wecom_native_failure_falls_back_to_cos_url(tmp_path: Path):
    secrets = SecretStore(tmp_path / "s.json")
    secrets.put(
        "wecom:default",
        {"bot_id": "b1", "secret": "s1", "allowed_users": ["*"]},
    )
    ws = tmp_path / "ws"
    ws.mkdir()
    (ws / "note.pdf").write_bytes(b"%PDF-1.4 data")
    texts: list[str] = []

    def failing_file(*_a, **_k):
        from coworker.connectors.base import SendResult

        return SendResult(False, error="upload_media unsupported")

    def text_sender(token, chat_id, text, thread_id=None):
        from coworker.connectors.base import SendResult

        texts.append(text)
        return SendResult(True, message_id="t1")

    store = MemoryFileStorage()
    tool = make_send_file_tool(
        secrets,
        workspace=ws,
        file_senders={"wecom": failing_file},
        text_senders={"wecom": text_sender},
        file_storage=store,
    )
    out = tool(target="wecom:user1", path="note.pdf")
    assert out.get("ok") is True
    assert out.get("delivery") == "cos_url"
    assert texts and "http" in texts[0]


def test_format_cos_url_message_includes_url():
    text = format_cos_url_message(
        filename="a.pdf", url="https://example.test/a.pdf", title="报告", comment="请查收"
    )
    assert "https://example.test/a.pdf" in text
    assert "报告" in text
    assert "请查收" in text


def test_deliver_file_slack_native_without_storage():
    from coworker.connectors.base import SendResult

    result = deliver_file(
        platform="slack",
        chat_id="C1",
        thread_id=None,
        token="tok",
        filename="a.pdf",
        data=b"%PDF-1.4",
        file_storage=NullFileStorage(),
        file_senders={
            "slack": lambda *a, **k: SendResult(True, message_id="F1"),
        },
        text_senders={},
    )
    assert result.ok
    assert result.delivery == "native"
