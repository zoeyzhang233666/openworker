"""Deterministic quote math — pure functions, no network, no invented prices."""

from __future__ import annotations

from dataclasses import dataclass, field
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP
from typing import Any, Optional

TOOL_VERSION = "1.0.0"
_MONEY = Decimal("0.01")
_QTY = Decimal("0.0001")


def _dec(value: Any, *, label: str) -> Decimal:
    if isinstance(value, bool) or value is None:
        raise ValueError(f"{label} must be a number")
    try:
        return Decimal(str(value))
    except (InvalidOperation, ValueError) as exc:
        raise ValueError(f"{label} is not a valid number") from exc


def _money(value: Decimal) -> str:
    return str(value.quantize(_MONEY, rounding=ROUND_HALF_UP))


def _qty(value: Decimal) -> str:
    # Keep compact decimal string without scientific notation.
    normalized = value.quantize(_QTY, rounding=ROUND_HALF_UP).normalize()
    text = format(normalized, "f")
    if "." in text:
        text = text.rstrip("0").rstrip(".")
    return text or "0"


@dataclass
class QuoteLineResult:
    line_id: str
    sku_id: str
    quantity: str
    unit: str
    unit_price: str
    line_total: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "line_id": self.line_id,
            "sku_id": self.sku_id,
            "quantity": self.quantity,
            "unit": self.unit,
            "unit_price": self.unit_price,
            "line_total": self.line_total,
        }


@dataclass
class QuoteCalcResult:
    status: str  # ok | needs_review | error
    currency: Optional[str] = None
    incoterm: Optional[str] = None
    lines: list[QuoteLineResult] = field(default_factory=list)
    subtotal: Optional[str] = None
    freight: Optional[str] = None
    tax: Optional[str] = None
    grand_total: Optional[str] = None
    warnings: list[str] = field(default_factory=list)
    missing_fields: list[str] = field(default_factory=list)
    error: Optional[str] = None
    calculator_version: str = TOOL_VERSION

    def to_dict(self) -> dict[str, Any]:
        return {
            "status": self.status,
            "currency": self.currency,
            "incoterm": self.incoterm,
            "lines": [line.to_dict() for line in self.lines],
            "subtotal": self.subtotal,
            "freight": self.freight,
            "tax": self.tax,
            "grand_total": self.grand_total,
            "warnings": list(self.warnings),
            "missing_fields": list(self.missing_fields),
            "error": self.error,
            "calculator_version": self.calculator_version,
        }


def calculate_quote(payload: dict[str, Any]) -> QuoteCalcResult:
    """Compute quote totals from explicit numeric inputs only.

    Formula (first pack):
      line_total = quantity * unit_price
      subtotal = sum(line_total)
      freight = freight (default 0 if omitted)
      tax = tax_amount if provided, else subtotal * tax_rate if tax_rate provided, else 0
      grand_total = subtotal + freight + tax
    """
    if not isinstance(payload, dict):
        return QuoteCalcResult(status="error", error="payload must be an object")

    missing: list[str] = []
    warnings: list[str] = []

    currency = payload.get("currency")
    if not isinstance(currency, str) or not currency.strip():
        missing.append("currency")

    incoterm = payload.get("incoterm")
    if incoterm is not None and (not isinstance(incoterm, str) or not incoterm.strip()):
        return QuoteCalcResult(status="error", error="incoterm must be a non-empty string or null")

    lines_in = payload.get("lines")
    if not isinstance(lines_in, list) or not lines_in:
        missing.append("lines")
        return QuoteCalcResult(
            status="needs_review",
            currency=currency.strip() if isinstance(currency, str) else None,
            incoterm=incoterm.strip() if isinstance(incoterm, str) else None,
            missing_fields=missing,
            warnings=["no quote lines provided"],
        )

    computed_lines: list[QuoteLineResult] = []
    subtotal = Decimal("0")

    for index, raw in enumerate(lines_in):
        prefix = f"lines[{index}]"
        if not isinstance(raw, dict):
            return QuoteCalcResult(status="error", error=f"{prefix} must be an object")
        line_id = raw.get("line_id") or f"line-{index + 1}"
        sku_id = raw.get("sku_id")
        unit = raw.get("unit")
        if not isinstance(line_id, str) or not line_id.strip():
            return QuoteCalcResult(status="error", error=f"{prefix}.line_id invalid")
        if not isinstance(sku_id, str) or not sku_id.strip():
            missing.append(f"{prefix}.sku_id")
            continue
        if not isinstance(unit, str) or not unit.strip():
            missing.append(f"{prefix}.unit")
            continue
        if "quantity" not in raw or raw.get("quantity") is None:
            missing.append(f"{prefix}.quantity")
            continue
        if "unit_price" not in raw or raw.get("unit_price") is None:
            missing.append(f"{prefix}.unit_price")
            continue
        try:
            quantity = _dec(raw["quantity"], label=f"{prefix}.quantity")
            unit_price = _dec(raw["unit_price"], label=f"{prefix}.unit_price")
        except ValueError as exc:
            return QuoteCalcResult(status="error", error=str(exc))
        if quantity <= 0:
            return QuoteCalcResult(status="error", error=f"{prefix}.quantity must be > 0")
        if unit_price < 0:
            return QuoteCalcResult(status="error", error=f"{prefix}.unit_price must be >= 0")
        line_total = quantity * unit_price
        subtotal += line_total
        computed_lines.append(
            QuoteLineResult(
                line_id=line_id.strip(),
                sku_id=sku_id.strip(),
                quantity=_qty(quantity),
                unit=unit.strip(),
                unit_price=_money(unit_price),
                line_total=_money(line_total),
            )
        )

    if missing:
        return QuoteCalcResult(
            status="needs_review",
            currency=currency.strip() if isinstance(currency, str) else None,
            incoterm=incoterm.strip() if isinstance(incoterm, str) else None,
            lines=computed_lines,
            missing_fields=missing,
            warnings=["explicit quantity and unit_price required; do not invent prices"],
        )

    freight_raw = payload.get("freight")
    tax_amount_raw = payload.get("tax_amount")
    tax_rate_raw = payload.get("tax_rate")

    try:
        freight = _dec(freight_raw, label="freight") if freight_raw is not None else Decimal("0")
    except ValueError as exc:
        return QuoteCalcResult(status="error", error=str(exc))
    if freight < 0:
        return QuoteCalcResult(status="error", error="freight must be >= 0")

    tax = Decimal("0")
    if tax_amount_raw is not None and tax_rate_raw is not None:
        return QuoteCalcResult(
            status="error",
            error="provide only one of tax_amount or tax_rate",
        )
    try:
        if tax_amount_raw is not None:
            tax = _dec(tax_amount_raw, label="tax_amount")
        elif tax_rate_raw is not None:
            tax_rate = _dec(tax_rate_raw, label="tax_rate")
            if tax_rate < 0:
                return QuoteCalcResult(status="error", error="tax_rate must be >= 0")
            tax = (subtotal + freight) * tax_rate
        else:
            warnings.append("tax omitted; treated as 0")
    except ValueError as exc:
        return QuoteCalcResult(status="error", error=str(exc))
    if tax < 0:
        return QuoteCalcResult(status="error", error="tax must be >= 0")

    grand = subtotal + freight + tax
    return QuoteCalcResult(
        status="ok",
        currency=currency.strip(),
        incoterm=incoterm.strip() if isinstance(incoterm, str) else None,
        lines=computed_lines,
        subtotal=_money(subtotal),
        freight=_money(freight),
        tax=_money(tax),
        grand_total=_money(grand),
        warnings=warnings,
        missing_fields=[],
    )
