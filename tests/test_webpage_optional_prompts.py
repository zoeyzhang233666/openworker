"""D-077/D-078: optional webpage + short bubble + price guidance (no auto-cook)."""

from pathlib import Path

from coworker.agent import _CLARIFY_POINTER, _LONG_TASK_GUIDANCE


def test_long_task_guidance_short_bubble_and_optional_webpage():
    text = _LONG_TASK_GUIDANCE
    assert "OPTIONAL" in text
    assert "align" in text.lower()
    assert "keep the chat bubble SHORT" in text
    assert "cooks an interactive webpage in the background" not in text
    assert "CDN" in text or "read-only GET" in text
    assert "second research agent" in text or "MCP/skills" in text


def test_clarify_pointer_short_bubble_and_align():
    text = _CLARIFY_POINTER
    assert "webpage" in text.lower()
    assert "align" in text.lower()
    assert "short" in text.lower()
    assert "Do not ask whether to make a nicer webpage" not in text


def test_chain_lobster_short_bubble_price_and_webpage():
    raw = (
        Path(__file__).resolve().parents[1]
        / "coworker"
        / "personas"
        / "builtin"
        / "chain-lobster.md"
    ).read_text(encoding="utf-8")
    assert "chem-price-daily" in raw
    assert "要点列表" in raw or "短" in raw
    assert "价格表" in raw
    assert "悬停" in raw or "走势图" in raw
    assert "网页版" in raw
    assert "对齐" in raw
    assert "后台烹饪" not in raw
