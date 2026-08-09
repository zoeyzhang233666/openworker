"""Deterministic calculate_quote Tool — no invented prices."""

from __future__ import annotations

from coworker.quote import calculate_quote, make_calculate_quote_tool


def test_ok_totals():
    result = calculate_quote(
        {
            "currency": "USD",
            "incoterm": "CIF",
            "freight": 100,
            "tax_rate": 0.1,
            "lines": [
                {
                    "line_id": "l1",
                    "sku_id": "sku-benzoate",
                    "quantity": 10,
                    "unit": "MT",
                    "unit_price": "1200.00",
                }
            ],
        }
    )
    assert result.status == "ok"
    assert result.subtotal == "12000.00"
    assert result.freight == "100.00"
    assert result.tax == "1210.00"  # (12000+100)*0.1
    assert result.grand_total == "13310.00"
    assert result.lines[0].line_total == "12000.00"
    assert result.error is None


def test_missing_unit_price_needs_review_no_invented_total():
    result = calculate_quote(
        {
            "currency": "USD",
            "lines": [
                {
                    "sku_id": "sku-1",
                    "quantity": 2,
                    "unit": "MT",
                    # unit_price omitted
                }
            ],
        }
    )
    assert result.status == "needs_review"
    assert any("unit_price" in m for m in result.missing_fields)
    assert result.grand_total is None


def test_tax_amount_and_rate_conflict_error():
    result = calculate_quote(
        {
            "currency": "EUR",
            "tax_amount": 10,
            "tax_rate": 0.1,
            "lines": [
                {
                    "sku_id": "sku-1",
                    "quantity": 1,
                    "unit": "KG",
                    "unit_price": 5,
                }
            ],
        }
    )
    assert result.status == "error"
    assert result.grand_total is None


def test_empty_lines_needs_review():
    result = calculate_quote({"currency": "USD", "lines": []})
    assert result.status == "needs_review"
    assert "lines" in result.missing_fields


def test_tool_wrapper_and_registration():
    tool = make_calculate_quote_tool()
    out = tool(
        currency="USD",
        lines=[
            {
                "sku_id": "sku-1",
                "quantity": "1.5",
                "unit": "MT",
                "unit_price": "2000",
            }
        ],
        freight=0,
    )
    assert out["status"] == "ok"
    assert out["grand_total"] == "3000.00"
    assert tool.__coworker_schema__["function"]["name"] == "calculate_quote"
    assert tool.__aisuite_tool_metadata__.requires_approval is False

    from coworker.agent import build_engine
    from coworker.agents import chat_agent

    class _Stub:
        def complete(self, **_kw):
            from coworker.providers import AssistantTurn

            return AssistantTurn()

        def capabilities(self, _model):
            from coworker.providers.base import ModelCapabilities

            return ModelCapabilities()

    eng = build_engine(agent=chat_agent(), provider=_Stub())
    assert "calculate_quote" in eng.registry.names()
