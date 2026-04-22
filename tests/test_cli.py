from __future__ import annotations

import json
from pathlib import Path
from textwrap import dedent

from typer.testing import CliRunner

import folio.commands.preview as preview_command_module
from folio.cache import cache_build, cache_paths
from folio.cli import app
from folio.dsl.loader import load_dsl_module
from folio.dsl.renderer import build_pages

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
