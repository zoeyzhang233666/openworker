from pathlib import Path


from coworker.outbound_clip import clip_tool_result, summarize_mcp_result


def test_clip_tool_result_overflow_written(tmp_path):
    workspace = Path(tmp_path)
    content = ("HEAD-" + ("A" * 10_000) + "-MIDDLE-" + ("B" * 10_000) + "-TAIL-") * 2

    clipped, overflow_rel = clip_tool_result(content, workspace_root=workspace, cap_chars=40_000)
    assert overflow_rel is not None
    assert overflow_rel in clipped
    assert len(clipped) <= 40_000

    overflow_path = workspace / overflow_rel
    assert overflow_path.exists()
    assert overflow_path.read_text(encoding="utf-8") == content


def test_clip_tool_result_is_idempotent_by_hash(tmp_path):
    workspace = Path(tmp_path)
    content = "x" * 41_000 + "y" * 1_000

    clipped1, overflow_rel1 = clip_tool_result(content, workspace_root=workspace, cap_chars=40_000)
    clipped2, overflow_rel2 = clip_tool_result(content, workspace_root=workspace, cap_chars=40_000)

    assert overflow_rel1 == overflow_rel2
    assert clipped1 == clipped2


def test_mcp_json_gets_structured_summary(tmp_path):
    workspace = Path(tmp_path)
    payload = {
        "q": "丙烯酸",
        "results": [{"name": "丙烯酸", "cas": "79-10-7"}] * 20,
        "notes": "x" * 50_000,
    }
    import json

    content = json.dumps(payload, ensure_ascii=False)
    clipped, overflow_rel = clip_tool_result(
        content,
        workspace_root=workspace,
        cap_chars=40_000,
        tool_name="mcp__chem_data_hub__search_compound",
    )
    assert overflow_rel is not None
    assert "MCP 结果摘要" in clipped
    assert "丙烯酸" in clipped
    assert overflow_rel in clipped
    summary = summarize_mcp_result(content, tool_name="mcp__chem_data_hub__search_compound")
    assert summary is not None and "results" in summary

