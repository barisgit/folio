from __future__ import annotations

from pathlib import Path
from textwrap import dedent

from typer.testing import CliRunner

from folio.cli import app
from folio.core.export.pdf import PdfExportError, PdfPage, write_pdf

runner = CliRunner()


def _write_png(path: Path, color: tuple[int, int, int] = (255, 0, 0)) -> None:
    from PIL import Image

    path.parent.mkdir(parents=True, exist_ok=True)
    Image.new("RGB", (24, 16), color=color).save(path)


def _pdf_page_count(pdf_path: Path) -> int:
    data = pdf_path.read_bytes()
    return data.count(b"/Type /Page") - data.count(b"/Type /Pages")


def test_write_pdf_rasterizes_rendered_pages_and_embeds_images(tmp_path: Path) -> None:
    rendered: list[str] = []

    def render_svg(svg_text: str, output_path: Path) -> Path:
        rendered.append(svg_text)
        _write_png(output_path)
        return output_path

    target = write_pdf(
        document=None,  # type: ignore[arg-type]
        out_dir=tmp_path,
        filename="visual.pdf",
        pages=(
            PdfPage(2, "<svg><text>second</text></svg>", 100, 50),
            PdfPage(1, "<svg><text>first</text></svg>", 100, 50),
        ),
        render_svg=render_svg,
    )

    data = target.read_bytes()
    assert target == tmp_path / "visual.pdf"
    assert rendered == ["<svg><text>first</text></svg>", "<svg><text>second</text></svg>"]
    assert b"/Image" in data
    assert _pdf_page_count(target) == 2


def test_write_pdf_removes_partial_file_when_rasterization_fails(tmp_path: Path) -> None:
    target = tmp_path / "broken.pdf"

    def fail_render(svg_text: str, output_path: Path) -> Path:
        raise RuntimeError("renderer exploded")

    try:
        write_pdf(
            document=None,  # type: ignore[arg-type]
            out_dir=tmp_path,
            filename=target.name,
            pages=(PdfPage(1, "<svg />", 100, 50),),
            render_svg=fail_render,
        )
    except PdfExportError as exc:
        assert "renderer exploded" in str(exc)
    else:  # pragma: no cover - assertion guard
        raise AssertionError("expected PdfExportError")

    assert not target.exists()
    assert not (tmp_path / "broken.pdf.tmp").exists()


def test_build_pdf_target_writes_visual_pdf_for_each_document(tmp_path: Path, monkeypatch) -> None:
    spec_path = tmp_path / "build.py"
    spec_path.write_text(
        dedent(
            """
            from folio.dsl import collection, document, page, pdf, rect

            def build():
                return collection(
                    document(
                        "brochure",
                        pages=[
                            page(
                                rect("b1_bg", 0, 0, 100, 50),
                                page_id="b1",
                                filename="b1.svg",
                                page_number=1,
                            ),
                            page(
                                rect("b2_bg", 0, 0, 100, 50),
                                page_id="b2",
                                filename="b2.svg",
                                page_number=2,
                            ),
                        ],
                        filename="brochure",
                        export_presets=[pdf()],
                        default_exports=["pdf"],
                    ),
                    document(
                        "tv",
                        pages=[
                            page(
                                rect("tv_bg", 0, 0, 192, 108),
                                page_id="tv",
                                filename="tv.svg",
                                page_number=1,
                            )
                        ],
                        filename="tv",
                        export_presets=[pdf()],
                        default_exports=["pdf"],
                    ),
                )
            """
        ).strip()
        + "\n",
        encoding="utf-8",
    )
    out_dir = tmp_path / "out"
    calls: list[str] = []

    def fake_render(svg_text: str, *, output_path: Path, viewport=None) -> Path:
        calls.append(svg_text)
        _write_png(output_path)
        return output_path

    monkeypatch.setattr("folio.core.export.pipeline._render_svg_preview", fake_render)

    command = runner.invoke(
        app,
        ["build", str(spec_path), "pdf", "--out-dir", str(out_dir), "--no-cache"],
    )

    assert command.exit_code == 0, command.stdout
    brochure_pdf = out_dir / "brochure.pdf"
    tv_pdf = out_dir / "tv.pdf"
    assert brochure_pdf.exists()
    assert tv_pdf.exists()
    assert b"/Image" in brochure_pdf.read_bytes()
    assert b"/Image" in tv_pdf.read_bytes()
    assert _pdf_page_count(brochure_pdf) == 2
    assert _pdf_page_count(tv_pdf) == 1
    assert len(calls) == 3


def test_build_pdf_target_reports_rasterization_failure(tmp_path: Path, monkeypatch) -> None:
    spec_path = tmp_path / "build.py"
    spec_path.write_text(
        dedent(
            """
            from folio.dsl import document, page, pdf, rect, collection

            def build():
                return collection(document(
                    "doc",
                    pages=[
                        page(
                            rect("bg", 0, 0, 100, 50),
                            page_id="p1",
                            filename="p1.svg",
                            page_number=1,
                        )
                    ],
                    export_presets=[pdf()],
                    default_exports=["pdf"],
                ))
            """
        ).strip()
        + "\n",
        encoding="utf-8",
    )

    def fail_render(svg_text: str, *, output_path: Path, viewport=None) -> Path:
        raise RuntimeError("no raster backend")

    monkeypatch.setattr("folio.core.export.pipeline._render_svg_preview", fail_render)

    command = runner.invoke(app, ["build", str(spec_path), "pdf", "--no-cache"])

    assert command.exit_code == 2
    assert "Could not export PDF" in command.stdout
    assert "no raster backend" in command.stdout
