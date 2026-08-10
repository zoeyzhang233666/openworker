"""Customs file provider — fixture contract tests (no network)."""

from __future__ import annotations

from pathlib import Path

from coworker.customs import CustomsFileProvider, make_filter_customs_importers_tool


FIXTURES = Path(__file__).resolve().parent / "fixtures" / "customs"


def test_filters_forwarders_and_ranks_real_importers():
    p = CustomsFileProvider()
    result = p.filter_importers(path=str(FIXTURES / "sample_shipments.csv"), limit=20)
    assert result.status == "ok"
    assert result.error is None
    assert any("终端买家" in w or "货代" in w for w in result.warnings)
    assert result.summary["raw_rows"] >= 10
    assert result.summary["companies"] >= 4

    by_name = {c["company_name"]: c for c in result.candidates}
    acme = by_name["Acme Specialty Chemicals Inc"]
    assert acme["recommendation"] == "likely_real_importer"
    assert acme["importer_likelihood"] >= 65
    assert "291829" in acme["hs_codes"]
    assert acme["shipment_count"] >= 3
    assert acme["evidence_summary"]

    freight = by_name["Global Freight Forwarders LLC"]
    assert freight["recommendation"] in (
        "exclude",
        "possible_freight_forwarder",
    )
    assert freight["recommendation"] != "likely_real_importer"
    assert freight["freight_forwarder_risk"] >= 45

    broker = by_name.get("Ocean Customs Brokerage Co")
    if broker:
        assert broker["recommendation"] in (
            "exclude",
            "possible_freight_forwarder",
            "needs_manual_review",
        )
        assert broker["recommendation"] != "likely_real_importer"

    assert result.source["provider_id"] == "customs_file"
    assert "company" in (result.source.get("columns") or {})


def test_missing_file_chinese_error():
    p = CustomsFileProvider()
    result = p.filter_importers(path=str(FIXTURES / "does-not-exist.csv"))
    assert result.status == "error"
    assert "找不到" in (result.error or "") or "文件" in (result.error or "")


def test_missing_company_column_chinese_error():
    p = CustomsFileProvider()
    result = p.filter_importers(path=str(FIXTURES / "missing_company.csv"))
    assert result.status == "error"
    assert "公司列" in (result.error or "") or "consignee" in (result.error or "").lower()


def test_empty_path_chinese_error():
    p = CustomsFileProvider()
    result = p.filter_importers(path="")
    assert result.status == "error"
    assert "路径" in (result.error or "") or "未提供" in (result.error or "")


def test_tool_wrapper_returns_dict():
    tool = make_filter_customs_importers_tool()
    out = tool(path=str(FIXTURES / "sample_shipments.csv"), limit=5)
    assert out["status"] == "ok"
    assert isinstance(out["candidates"], list)
    assert len(out["candidates"]) <= 5
    assert out["warnings"]


def test_xlsx_matches_csv_recommendations():
    p = CustomsFileProvider()
    csv_result = p.filter_importers(path=str(FIXTURES / "sample_shipments.csv"))
    xlsx_result = p.filter_importers(path=str(FIXTURES / "sample_shipments.xlsx"))
    assert xlsx_result.status == "ok"
    assert csv_result.status == "ok"
    csv_by = {c["company_name"]: c["recommendation"] for c in csv_result.candidates}
    xlsx_by = {c["company_name"]: c["recommendation"] for c in xlsx_result.candidates}
    assert xlsx_by["Acme Specialty Chemicals Inc"] == "likely_real_importer"
    assert csv_by["Acme Specialty Chemicals Inc"] == xlsx_by["Acme Specialty Chemicals Inc"]
    assert xlsx_by["Global Freight Forwarders LLC"] != "likely_real_importer"
    assert any("终端买家" in w or "货代" in w for w in xlsx_result.warnings)


def test_xlsx_missing_company_column_chinese_error():
    p = CustomsFileProvider()
    result = p.filter_importers(path=str(FIXTURES / "missing_company.xlsx"))
    assert result.status == "error"
    assert "公司列" in (result.error or "") or "consignee" in (result.error or "").lower()


def test_xls_extension_chinese_error(tmp_path: Path):
    fake = tmp_path / "legacy.xls"
    fake.write_bytes(b"not-a-real-xls")
    p = CustomsFileProvider()
    result = p.filter_importers(path=str(fake))
    assert result.status == "error"
    assert ".xls" in (result.error or "") or "xlsx" in (result.error or "").lower()
