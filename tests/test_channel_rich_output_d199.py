from __future__ import annotations

from pathlib import Path

import pytest

from coworker.channels.rich_output import (
    channel_visible_text,
    compose_channel_rich_reply,
    has_renderer_blocks,
    needs_channel_html_delivery,
)

PREVIEW_PNG = b"\x89PNG\r\n\x1a\npreview"
from coworker.connectors.base import SendResult
from coworker.connectors.tools import make_send_message_tool
from coworker.filestore.memory import MemoryFileStorage
from coworker.providers import AssistantTurn, ModelCapabilities, ProviderClient, StreamChunk
from coworker.secrets import SecretStore
from coworker.server.manager import SessionManager


CHART_REPLY = """结论：价格先降后稳。

```chart
{"version":1,"type":"line","title":"甲醇价格","labels":["08-30","08-31"],"series":[{"name":"现货","values":[2410,2420]}]}
```

后续可继续查看区域价差。"""


def test_renderer_blocks_are_hidden_but_normal_code_is_preserved():
    assert has_renderer_blocks(CHART_REPLY)
    visible = channel_visible_text(CHART_REPLY, final=True)
    assert "结论：价格先降后稳" in visible
    assert "后续可继续" in visible
    assert "```chart" not in visible
    assert "2410" not in visible

    partial = CHART_REPLY.split("```\n", 1)[0]
    assert channel_visible_text(partial, final=False) == "结论：价格先降后稳。"
    ordinary = "示例：\n```json\n{\"value\": 1}\n```\n结束"
    assert channel_visible_text(ordinary, final=True) == ordinary


def test_rich_reply_cooks_chart_html_and_uploads_link(tmp_path: Path):
    storage = MemoryFileStorage(pub_url="https://cos.example/")
    reply = compose_channel_rich_reply(
        assistant_text=CHART_REPLY,
        workspace=tmp_path,
        file_storage=storage,
        render_preview=lambda _path: PREVIEW_PNG,
    )
    assert reply.has_rich_blocks
    assert reply.html_url and "查看交互图表" in reply.text
    assert reply.preview_image_bytes == PREVIEW_PNG
    assert "```chart" not in reply.text and "2410" not in reply.text
    uploaded = next(iter(storage.objects.values())).decode("utf-8")
    assert "甲醇价格" in uploaded
    assert "chemclaw-chart-0" in uploaded
    assert "2410" in uploaded and "2420" in uploaded


def test_report_md_takes_priority_over_inline_chart(tmp_path: Path):
    report = tmp_path / "甲醇研究.md"
    report.write_text(
        "# 甲醇研究\n\n```chart\n"
        '{"version":1,"type":"line","title":"报告内甲醇","labels":["07-01","07-02"],'
        '"series":[{"name":"华东","values":[2500,2510]}]}\n```\n',
        encoding="utf-8",
    )
    storage = MemoryFileStorage(pub_url="https://cos.example/")
    reply = compose_channel_rich_reply(
        assistant_text=CHART_REPLY + f"\n\n详见 [报告](artifact:{report.name})",
        workspace=tmp_path,
        file_storage=storage,
        render_preview=lambda _path: PREVIEW_PNG,
    )
    assert reply.html_url and "查看完整版" in reply.text
    assert "查看交互图表" not in reply.text
    uploaded = next(iter(storage.objects.values())).decode("utf-8")
    assert "报告内甲醇" in uploaded
    assert "2410" not in uploaded
    assert needs_channel_html_delivery(CHART_REPLY, tmp_path)


def test_plain_reply_without_chart_or_report_is_text_only(tmp_path: Path):
    reply = compose_channel_rich_reply(
        assistant_text="今天天气不错。",
        workspace=tmp_path,
        file_storage=MemoryFileStorage(pub_url="https://cos.example/"),
    )
    assert reply.delivery_mode == "summary_only"
    assert reply.html_url is None
    assert not reply.preview_image_bytes


def test_send_message_telegram_replaces_chart_json_with_html_link(tmp_path: Path):
    secrets = SecretStore(tmp_path / "secrets.json")
    secrets.put("telegram:default", {"type": "token", "bot_token": "T0K"})
    sent: list[str] = []

    def sender(token, chat_id, text, thread_id=None):
        sent.append(text)
        return SendResult(True, message_id="m1")

    storage = MemoryFileStorage(pub_url="https://cos.example/")
    tool = make_send_message_tool(
        secrets,
        senders={"telegram": sender},
        workspace=tmp_path,
        file_storage=storage,
    )
    result = tool(target="telegram:123", text=CHART_REPLY)
    assert result["ok"]
    assert len(sent) == 1
    assert "查看交互图表" in sent[0]
    assert "```chart" not in sent[0] and "2410" not in sent[0]
    assert storage.objects


def test_send_message_without_cloud_never_falls_back_to_raw_chart_json(tmp_path: Path):
    secrets = SecretStore(tmp_path / "secrets.json")
    secrets.put("telegram:default", {"type": "token", "bot_token": "T0K"})
    sent: list[str] = []

    def sender(token, chat_id, text, thread_id=None):
        sent.append(text)
        return SendResult(True, message_id="m1")

    tool = make_send_message_tool(
        secrets,
        senders={"telegram": sender},
        file_senders={},
        workspace=tmp_path,
    )
    result = tool(target="telegram:123", text=CHART_REPLY)
    assert result["ok"]
    assert "网页发送失败" in sent[0]
    assert "```chart" not in sent[0] and '"values"' not in sent[0]


def test_send_message_native_channel_sends_safe_comment_and_html_file(tmp_path: Path):
    secrets = SecretStore(tmp_path / "secrets.json")
    secrets.put("wecom:default", {"bot_id": "bot-1", "secret": "secret"})
    text_calls: list[str] = []
    files: list[tuple[str, bytes, str | None]] = []

    def sender(token, chat_id, text, thread_id=None):
        text_calls.append(text)
        return SendResult(True, message_id="text")

    def file_sender(token, chat_id, thread_id, filename, data, title=None, comment=None):
        files.append((filename, data, comment))
        return SendResult(True, message_id="file")

    tool = make_send_message_tool(
        secrets,
        senders={"wecom": sender},
        file_senders={"wecom": file_sender},
        workspace=tmp_path,
    )
    result = tool(target="wecom:user", text=CHART_REPLY)
    assert result["ok"] and result["delivery"] == "native"
    assert not text_calls
    html_files = [item for item in files if item[0].endswith(".html")]
    assert html_files
    assert "chemclaw-chart-0" in html_files[0][1].decode("utf-8")
    assert "```chart" not in (html_files[0][2] or "")
    assert "2410" not in (html_files[0][2] or "")


class _ChartStreamingProvider(ProviderClient):
    answer = ("先给结论。" * 40) + "\n\n" + CHART_REPLY + "\n\n" + ("补充说明。" * 40)

    def complete(self, **kwargs):  # pragma: no cover
        raise NotImplementedError

    def capabilities(self, model):
        return ModelCapabilities()

    def stream(self, *, model, messages, tools=None, **settings):
        cut = self.answer.index("```chart") + 80
        yield StreamChunk(text_delta=self.answer[:cut])
        yield StreamChunk(text_delta=self.answer[cut:])
        yield StreamChunk(turn=AssistantTurn(text=self.answer, finish_reason="stop"))


class _CaptureGateway:
    def __init__(self):
        self.envelopes = []
        self.stream_updates: list[str] = []

    async def deliver_envelope(self, target, envelope):
        self.envelopes.append((target, envelope))
        return SendResult(True, message_id=f"m-{len(self.envelopes)}")

    async def update_stream(self, target, text):
        self.stream_updates.append(text)
        return SendResult(True, message_id="stream")


@pytest.mark.asyncio
@pytest.mark.parametrize("platform", ["wecom", "weixin", "feishu", "dingtalk"])
async def test_channel_stream_and_final_never_expose_chart_json(tmp_path: Path, platform: str):
    manager = SessionManager(
        workspace=tmp_path,
        data_dir=tmp_path / "data",
        provider=_ChartStreamingProvider(),
    )
    gateway = _CaptureGateway()
    manager.gateway = gateway  # type: ignore[assignment]
    session_id = f"{platform}-rich"
    target = f"{platform}:owner"
    engine = manager.get_engine(session_id, agent=manager.personas.default_id())
    assert engine is not None
    manager.save(session_id, engine)
    manager.mention_sessions.set(target, session_id, channel=f"{platform}:owner")

    await manager.deliver_to_session(
        session_id,
        "请看图",
        source={
            "connector": platform,
            "kind": "dm",
            "text": "请看图",
            "target": target,
            "message_id": "in-1",
        },
    )

    all_text = "\n".join(
        gateway.stream_updates
        + [envelope.text for _target, envelope in gateway.envelopes]
    )
    assert "```chart" not in all_text
    assert '"values"' not in all_text
    final = gateway.envelopes[-1][1]
    assert final.kind == "final"
    assert final.attachments
    html_attachments = [a for a in final.attachments if a.name.endswith(".html")]
    assert html_attachments
    assert Path(html_attachments[0].local_path).read_text(encoding="utf-8").find(
        "chemclaw-chart-0"
    ) > 0
