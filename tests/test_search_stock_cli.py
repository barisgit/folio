from __future__ import annotations

import json

from typer.testing import CliRunner

import folio.commands.search.stock as stock_mod
from folio.cli import app
from folio.search.providers import SearchResult

runner = CliRunner()


def _fake_results(*args, **kwargs):
    return [
        SearchResult(
            id="abc-123",
            provider="openverse",
            description="A sunset over the ocean",
            url="https://example.com/photo/abc-123",
            thumbnail="https://example.com/thumb/abc-123",
            width=1920,
            height=1080,
            license="cc0",
            creator="Jane Doe",
            source="Wikimedia",
        ),
        SearchResult(
            id="def-456",
            provider="openverse",
            description="Mountain landscape",
            url="https://example.com/photo/def-456",
            thumbnail="https://example.com/thumb/def-456",
            width=800,
            height=600,
            license="cc-by",
            creator="John Smith",
            source="Flickr",
        ),
    ]



def test_search_stock_prints_table(monkeypatch) -> None:
    monkeypatch.setattr(stock_mod, "fetch_stock", _fake_results)

    result = runner.invoke(app, ["search", "stock", "sunset"])

    assert result.exit_code == 0
    assert "sunset over the ocean" in result.stdout
    assert "1920×1080" in result.stdout



def test_search_stock_json_output(monkeypatch) -> None:
    monkeypatch.setattr(stock_mod, "fetch_stock", _fake_results)

    result = runner.invoke(app, ["search", "stock", "sunset", "--json"])

    assert result.exit_code == 0
    payload = json.loads(result.stdout)
    assert len(payload) == 2
    assert payload[0]["id"] == "abc-123"
    assert payload[0]["width"] == 1920
    assert payload[1]["description"] == "Mountain landscape"



def test_search_stock_provider_option(monkeypatch) -> None:
    captured: dict = {}

    def _capture(*args, **kwargs):
        captured.update(kwargs)
        return _fake_results()

    monkeypatch.setattr(stock_mod, "fetch_stock", _capture)

    result = runner.invoke(app, ["search", "stock", "trees", "--provider", "pexels"])

    assert result.exit_code == 0
    assert captured["provider"] == "pexels"


def test_search_stock_multiple_provider_options(monkeypatch) -> None:
    captured: dict = {}

    def _capture_multi(*args, **kwargs):
        captured.update(kwargs)
        return _fake_results()

    monkeypatch.setattr(stock_mod, "fetch_stock_multi", _capture_multi)

    result = runner.invoke(
        app,
        ["search", "stock", "trees", "--provider", "openverse", "--provider", "pixabay"],
    )

    assert result.exit_code == 0
    assert captured["providers"] == ["openverse", "pixabay"]


def test_search_stock_provider_all(monkeypatch) -> None:
    captured: dict = {}

    def _capture_multi(*args, **kwargs):
        captured.update(kwargs)
        return _fake_results()

    monkeypatch.setattr(stock_mod, "fetch_stock_multi", _capture_multi)

    result = runner.invoke(app, ["search", "stock", "trees", "--provider", "all"])

    assert result.exit_code == 0
    assert captured["providers"] == ["openverse", "pexels", "pixabay"]


def test_search_stock_invalid_provider(monkeypatch) -> None:
    result = runner.invoke(app, ["search", "stock", "trees", "--provider", "nonexistent"])

    assert result.exit_code == 1
    assert "Unknown provider" in result.stdout
    assert "nonexistent" in result.stdout



def test_search_stock_per_page_option(monkeypatch) -> None:
    captured: dict = {}

    def _capture(*args, **kwargs):
        captured.update(kwargs)
        return _fake_results()

    monkeypatch.setattr(stock_mod, "fetch_stock", _capture)

    result = runner.invoke(app, ["search", "stock", "cats", "--per-page", "5"])

    assert result.exit_code == 0
    assert captured["per_page"] == 5



def test_search_stock_empty_results(monkeypatch) -> None:
    monkeypatch.setattr(stock_mod, "fetch_stock", lambda *a, **kw: [])

    result = runner.invoke(app, ["search", "stock", "obscure-query"])

    assert result.exit_code == 0
    assert "No results found" in result.stdout



def test_search_stock_missing_api_key_exits(monkeypatch) -> None:
    def _raise(*args, **kwargs):
        raise RuntimeError("PEXELS_API_KEY environment variable is required for Pexels.")

    monkeypatch.setattr(stock_mod, "fetch_stock", _raise)

    result = runner.invoke(app, ["search", "stock", "test", "--provider", "pexels"])

    assert result.exit_code == 1
    assert "PEXELS_API_KEY" in result.stdout



def test_search_stock_json_output_includes_metadata(monkeypatch) -> None:
    monkeypatch.setattr(stock_mod, "fetch_stock", _fake_results)

    result = runner.invoke(app, ["search", "stock", "sunset", "--json"])

    assert result.exit_code == 0
    payload = json.loads(result.stdout)
    assert payload[0]["license"] == "cc0"
    assert payload[0]["creator"] == "Jane Doe"
    assert payload[0]["source"] == "Wikimedia"
    assert payload[1]["license"] == "cc-by"


def test_search_stock_no_args_shows_help() -> None:
    result = runner.invoke(app, ["search"])

    assert result.exit_code in (0, 2)
    assert "stock" in result.stdout
