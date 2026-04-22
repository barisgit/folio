from __future__ import annotations

import json

from typer.testing import CliRunner

import folio.commands.search.svg as search_svg_command_module
from folio.cli import app
from folio.search.svg import SvgSearchError, SvgSearchResponse, SvgSearchResult, search_svg_assets

runner = CliRunner()


def test_search_svg_command_renders_table(monkeypatch) -> None:
    def fake_search_svg_assets(query: str, *, limit: int = 8, sources=()):
        assert query == "stripe"
        assert limit == 8
        assert tuple(sources) == ()
        return SvgSearchResponse(
            query=query,
            results=[
                SvgSearchResult(
                    source="svgl",
                    title="Stripe",
                    svg_url="https://svgl.app/library/stripe.svg",
                    subtitle="payments",
                    website="https://stripe.com",
                    verified=True,
                )
            ],
            warnings=["iconify lookup failed: timeout"],
        )

    monkeypatch.setattr(search_svg_command_module, "search_svg_assets", fake_search_svg_assets)

    command = runner.invoke(app, ["search", "svg", "stripe"])

    assert command.exit_code == 0
    assert "Stripe" in command.stdout
    assert "svgl" in command.stdout
    assert "stripe.com" in command.stdout
    assert "iconify lookup failed: timeout" in command.stdout


def test_search_svg_command_can_emit_json(monkeypatch) -> None:
    def fake_search_svg_assets(query: str, *, limit: int = 8, sources=()):
        return SvgSearchResponse(
            query=query,
            results=[
                SvgSearchResult(
                    source="iconify",
                    title="lucide:trash-2",
                    svg_url="https://api.iconify.design/lucide/trash-2.svg",
                    subtitle="Lucide",
                    identifier="lucide:trash-2",
                    verified=True,
                )
            ],
            warnings=[],
        )

    monkeypatch.setattr(search_svg_command_module, "search_svg_assets", fake_search_svg_assets)

    command = runner.invoke(app, ["search", "svg", "trash", "--json"])

    assert command.exit_code == 0
    payload = json.loads(command.stdout)
    assert payload == {
        "query": "trash",
        "results": [
            {
                "source": "iconify",
                "title": "lucide:trash-2",
                "svg_url": "https://api.iconify.design/lucide/trash-2.svg",
                "subtitle": "Lucide",
                "identifier": "lucide:trash-2",
                "website": None,
                "wordmark_url": None,
                "verified": True,
            }
        ],
        "warnings": [],
    }


def test_search_svg_command_reports_errors(monkeypatch) -> None:
    def fake_search_svg_assets(query: str, *, limit: int = 8, sources=()):
        raise SvgSearchError("boom")

    monkeypatch.setattr(search_svg_command_module, "search_svg_assets", fake_search_svg_assets)

    command = runner.invoke(app, ["search", "svg", "stripe"])

    assert command.exit_code == 1
    assert "SVG search error:" in command.stdout
    assert "boom" in command.stdout


def test_search_svg_assets_ranks_and_verifies_results(monkeypatch) -> None:
    def fake_fetch_json(url: str):
        if url.startswith("https://api.svgl.app"):
            return [
                {
                    "title": "Stripe",
                    "category": "payments",
                    "route": "https://svgl.app/library/stripe.svg",
                    "url": "https://stripe.com",
                }
            ]
        if url.startswith("https://api.iconify.design/search"):
            return {
                "icons": ["logos:stripe", "mdi:credit-card"],
                "collections": {
                    "logos": {"name": "Logos"},
                    "mdi": {"name": "Material Design Icons"},
                },
            }
        raise AssertionError(url)

    def fake_probe(url: str) -> bool:
        return url in {
            "https://svgl.app/library/stripe.svg",
            "https://cdn.simpleicons.org/stripe",
            "https://api.iconify.design/logos/stripe.svg",
        }

    monkeypatch.setattr("folio.search.svg._fetch_json", fake_fetch_json)
    monkeypatch.setattr("folio.search.svg._probe_svg_url", fake_probe)

    response = search_svg_assets("stripe", limit=3)

    assert [result.source for result in response.results] == ["svgl", "simple-icons", "iconify"]
    assert response.results[0].title == "Stripe"
    assert response.results[1].identifier == "stripe"
    assert response.results[2].identifier == "logos:stripe"
    assert response.warnings == []
