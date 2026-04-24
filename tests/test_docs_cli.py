from __future__ import annotations

import json

import pytest
from typer.testing import CliRunner

from folio.cli import app

runner = CliRunner()


def test_show_known_symbol_returns_zero() -> None:
    result = runner.invoke(app, ["docs", "show", "page"])
    assert result.exit_code == 0
    assert "folio.dsl.page" in result.stdout


def test_show_unknown_symbol_returns_two_with_hint() -> None:
    result = runner.invoke(app, ["docs", "show", "raect"])
    assert result.exit_code == 2
    combined = result.output
    assert "unknown symbol" in combined
    assert "rect" in combined


def test_show_supports_json_format() -> None:
    result = runner.invoke(app, ["docs", "show", "folio.dsl.page", "--format", "json"])
    assert result.exit_code == 0
    payload = json.loads(result.stdout)
    assert payload["id"] == "folio.dsl.page"
    assert payload["kind"] == "primitive"


def test_show_accepts_json_shortcut() -> None:
    result = runner.invoke(app, ["docs", "show", "page", "--json"])
    assert result.exit_code == 0
    payload = json.loads(result.stdout)
    assert payload["id"] == "folio.dsl.page"


def test_conflicting_format_flags_exit_one() -> None:
    result = runner.invoke(app, ["docs", "show", "page", "--json", "--format", "md"])
    assert result.exit_code == 1
    combined = result.output
    assert "conflicting" in combined.lower() or "cannot be combined" in combined


def test_search_returns_results() -> None:
    result = runner.invoke(app, ["docs", "search", "rect", "--json"])
    assert result.exit_code == 0
    payload = json.loads(result.stdout)
    assert payload["query"] == "rect"
    assert any("rect" in sym["id"] for sym in payload["matches"])


def test_search_empty_exit_zero() -> None:
    result = runner.invoke(app, ["docs", "search", "zzzzzz_no_match", "--json"])
    assert result.exit_code == 0
    payload = json.loads(result.stdout)
    assert payload["matches"] == []


def test_list_filters_by_kind() -> None:
    result = runner.invoke(app, ["docs", "list", "--kind", "token", "--json"])
    assert result.exit_code == 0
    payload = json.loads(result.stdout)
    assert all(sym["kind"] == "token" for sym in payload["symbols"])


def test_list_rejects_invalid_kind() -> None:
    result = runner.invoke(app, ["docs", "list", "--kind", "bogus"])
    assert result.exit_code == 1
    combined = result.output
    assert "invalid kind" in combined.lower()


def test_schema_mismatch_exits_three(monkeypatch: pytest.MonkeyPatch, tmp_path: object) -> None:
    stub = tmp_path
    bad_path = stub / "index.json"  # type: ignore[operator]
    bad_path.write_text(json.dumps({"version": 99, "symbols": []}), encoding="utf-8")

    from folio.cli import docs as docs_module

    monkeypatch.setattr(docs_module, "index_path", lambda: bad_path)

    result = runner.invoke(app, ["docs", "list"])
    assert result.exit_code == 3
    combined = result.output
    assert "schema mismatch" in combined.lower()


def test_missing_index_file_exits_three(monkeypatch: pytest.MonkeyPatch, tmp_path: object) -> None:
    missing = tmp_path / "missing.json"  # type: ignore[operator]

    from folio.cli import docs as docs_module

    monkeypatch.setattr(docs_module, "index_path", lambda: missing)

    result = runner.invoke(app, ["docs", "list"])
    assert result.exit_code == 3
    combined = result.output
    assert "doc index missing" in combined.lower()
