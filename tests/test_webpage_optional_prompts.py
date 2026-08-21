"""D-077/D-078: optional webpage + short bubble + price guidance (no auto-cook)."""

from pathlib import Path

from coworker.agent import _CLARIFY_POINTER, _LONG_TASK_GUIDANCE


def test_long_task_guidance_short_bubble_and_optional_webpage():
    text = _LONG_TASK_GUIDANCE
    assert "可选" in text
    assert "对齐" in text
    assert "气泡要短" in text
    assert "后台烹饪" not in text
    assert "CDN" in text or "只读" in text
    assert "第二套" in text or "MCP" in text


def test_clarify_pointer_short_bubble_and_align():
    text = _CLARIFY_POINTER
    assert "网页版" in text
    assert "对齐" in text
    assert "短" in text
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
