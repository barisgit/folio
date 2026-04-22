from __future__ import annotations

import json
from pathlib import Path
from textwrap import dedent

from typer.testing import CliRunner

import folio.commands.preview as preview_command_module
import folio.commands.search.stock as stock_mod
from folio.cache import cache_build, cache_paths
from folio.cli import app
from folio.dsl.loader import load_dsl_module
from folio.dsl.renderer import build_pages
from folio.search.providers import SearchResult

runner = CliRunner()

def test_preview_can_render_arbitrary_svg_path(
    tmp_path: Path,
    monkeypatch,
) -> None:
    svg_path = tmp_path / "cover.svg"
    svg_path.write_text('<svg xmlns="http://www.w3.org/2000/svg"></svg>\n', encoding="utf-8")
    output_path = tmp_path / "preview.png"
    captured: dict[str, object] = {}

    def fake_render_preview_file(
        preview_svg: Path,
        *,
        output_path: Path | None = None,
        viewport: tuple[int, int] | None = None,
    ) -> Path:
        captured["svg_path"] = preview_svg
        captured["output_path"] = output_path
        captured["viewport"] = viewport
        target = output_path or preview_svg.with_suffix(".png")
        target.write_bytes(b"PNG")
        return target

    monkeypatch.setattr(
        preview_command_module,
        "render_preview_file",
        fake_render_preview_file,
    )

    command = runner.invoke(
        app,
        [
            "preview",
            str(svg_path),
            "--output",
            str(output_path),
            "--viewport",
            "800x600",
        ],
    )

    assert command.exit_code == 0
    assert output_path.exists()
    assert captured == {
        "svg_path": svg_path,
        "output_path": output_path,
        "viewport": (800, 600),
    }


def test_preview_rejects_output_without_svg_path(tmp_path: Path) -> None:
    command = runner.invoke(
        app,
        ["preview", "--output", str(tmp_path / "preview.png")],
    )

    assert command.exit_code == 2


def test_build_can_write_one_page_without_cache(tmp_path: Path) -> None:
    spec_path = tmp_path / "spec.py"
    spec_path.write_text(
        dedent(
            """
            from folio.dsl import page, render, text

            def build():
                return render(
                    page(
                        page_id="one",
                        filename="one.svg",
                        page_number=1,
                        elements=[text("line1", 10, 20, "One", size_pt=12)],
                    ),
                    page(
                        page_id="two",
                        filename="two.svg",
                        page_number=2,
                        elements=[text("line2", 10, 20, "Two", size_pt=12)],
                    ),
                )
            """
        ).strip()
        + "\n",
        encoding="utf-8",
    )
    out_dir = tmp_path / "out"

    command = runner.invoke(
        app,
        [
            "build",
            str(spec_path),
            "--page",
            "2",
            "--out-dir",
            str(out_dir),
            "--no-cache",
        ],
    )

    assert command.exit_code == 0
    assert (out_dir / "two.svg").exists()
    assert not (out_dir / "one.svg").exists()
    assert not cache_paths(spec_path).root.exists()



def test_build_uses_project_build_py_by_default(tmp_path: Path, monkeypatch) -> None:
    project_dir = tmp_path / "project"
    project_dir.mkdir()
    build_path = project_dir / "build.py"
    build_path.write_text(
        dedent(
            """
            from folio.dsl import page, render, text

            def build():
                return render(
                    page(
                        page_id="cover",
                        filename="cover.svg",
                        page_number=1,
                        elements=[text("headline", 10, 20, "Hello", size_pt=12)],
                    )
                )
            """
        ).strip()
        + "\n",
        encoding="utf-8",
    )

    monkeypatch.chdir(project_dir)
    command = runner.invoke(app, ["build", "--no-cache"])

    assert command.exit_code == 0
    assert (project_dir / "out" / "cover.svg").exists()
    assert not cache_paths(build_path).root.exists()



def test_build_accepts_project_directory_as_spec(tmp_path: Path) -> None:
    project_dir = tmp_path / "project"
    project_dir.mkdir()
    build_path = project_dir / "build.py"
    build_path.write_text(
        dedent(
            """
            from folio.dsl import page, render, text

            def build():
                return render(
                    page(
                        page_id="cover",
                        filename="cover.svg",
                        page_number=1,
                        elements=[text("headline", 10, 20, "Hello", size_pt=12)],
                    )
                )
            """
        ).strip()
        + "\n",
        encoding="utf-8",
    )

    out_dir = project_dir / "rendered"
    command = runner.invoke(
        app,
        ["build", str(project_dir), "--out-dir", str(out_dir), "--no-cache"],
    )

    assert command.exit_code == 0
    assert (out_dir / "cover.svg").exists()
    assert not cache_paths(build_path).root.exists()



def test_build_defaults_to_spec_local_out_dir_for_explicit_spec(
    tmp_path: Path,
    monkeypatch,
) -> None:
    project_dir = tmp_path / "project"
    project_dir.mkdir()
    outside_dir = tmp_path / "outside"
    outside_dir.mkdir()
    spec_path = project_dir / "build.py"
    spec_path.write_text(
        dedent(
            """
            from folio.dsl import page, render, text

            def build():
                return render(
                    page(
                        page_id="cover",
                        filename="cover.svg",
                        page_number=1,
                        elements=[text("headline", 10, 20, "Hello", size_pt=12)],
                    )
                )
            """
        ).strip()
        + "\n",
        encoding="utf-8",
    )

    monkeypatch.chdir(outside_dir)
    command = runner.invoke(app, ["build", str(spec_path), "--no-cache"])

    assert command.exit_code == 0
    assert (project_dir / "out" / "cover.svg").exists()
    assert not (outside_dir / "out" / "cover.svg").exists()


def test_reconcile_can_override_page_number(tmp_path: Path) -> None:
    spec_path = tmp_path / "spec.py"
    spec_path.write_text(
        dedent(
            """
            from folio.dsl import page, render, text

            def build():
                return render(
                    page(
                        page_id="one",
                        filename="one.svg",
                        page_number=1,
                        elements=[text("line1", 10, 20, "One", size_pt=12)],
                    ),
                    page(
                        page_id="two",
                        filename="two.svg",
                        page_number=2,
                        elements=[text("line2", 10, 20, "Two", size_pt=12)],
                    ),
                )
            """
        ).strip()
        + "\n",
        encoding="utf-8",
    )

    result = build_pages(load_dsl_module(spec_path), config_dir=spec_path.parent)
    cache_build(result, spec_path=spec_path)

    edited_svg = tmp_path / "edited.svg"
    edited_svg.write_text(
        result.pages[1].content
        .replace('data-page-number="2"', 'data-page-number=""')
        .replace(">Two</text>", ">Two again</text>"),
        encoding="utf-8",
    )

    command = runner.invoke(
        app,
        [
            "reconcile",
            str(edited_svg),
            "--spec",
            str(spec_path),
            "--page",
            "2",
            "--format",
            "json",
        ],
    )

    assert command.exit_code == 3
    payload = json.loads(command.stdout)
    assert payload["page_number"] == 2
    assert payload["page_id"] == "two"
    assert payload["changes"] == [
        {
            "id": "line2",
            "kind": "attribute",
            "attrs": {
                "text": {
                    "from": "Two",
                    "to": "Two again",
                }
            },
        }
    ]



def test_reconcile_rejects_page_with_all() -> None:
    command = runner.invoke(app, ["reconcile", "--all", "--page", "1"])

    assert command.exit_code == 2



def test_reconcile_json_output_is_machine_readable(tmp_path: Path) -> None:
    spec_path = tmp_path / "spec.py"
    spec_path.write_text(
        dedent(
            """
            from folio.dsl import page, render, text, tokens

            def build():
                return render(
                    page(
                        page_id="cover",
                        filename="cover.svg",
                        page_number=1,
                        elements=[
                            text("headline", 10, 20, "Hello", style=tokens.STYLES.body),
                        ],
                    )
                )
            """
        ).strip()
        + "\n",
        encoding="utf-8",
    )

    result = build_pages(load_dsl_module(spec_path), config_dir=spec_path.parent)
    cache_build(result, spec_path=spec_path)

    edited_svg = tmp_path / "cover-edited.svg"
    edited_svg.write_text(
        result.pages[0].content.replace(">Hello</text>", ">Hello again</text>"),
        encoding="utf-8",
    )

    command = runner.invoke(
        app,
        [
            "reconcile",
            str(edited_svg),
            "--spec",
            str(spec_path),
            "--format",
            "json",
        ],
    )

    assert command.exit_code == 3
    payload = json.loads(command.stdout)
    assert payload["page_number"] == 1
    assert payload["page_id"] == "cover"
    assert payload["unmatched_added"] == []
    assert payload["unmatched_removed"] == []
    assert payload["changes"] == [
        {
            "id": "headline",
            "kind": "attribute",
            "attrs": {
                "text": {
                    "from": "Hello",
                    "to": "Hello again",
                }
            },
        }
    ]
    assert payload["report_path"].endswith("_p1.json")


# --- create command tests ---
# Dedicated coverage lives in tests/test_create_cli.py.


# --- search stock command tests ---

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


def test_search_stock_no_args_shows_help() -> None:
    result = runner.invoke(app, ["search"])
    assert result.exit_code in (0, 2)  # Typer exits 0 or 2 depending on version
    assert "stock" in result.stdout

