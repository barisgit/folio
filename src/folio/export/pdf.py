from __future__ import annotations

import tempfile
from collections.abc import Callable, Sequence
from dataclasses import dataclass
from pathlib import Path

from folio.dsl.model import Document
from folio.preview import _render_svg_preview

_DEFAULT_PDF_NAME = "folio.pdf"
_PDF_RASTER_DPI = 300
_MM_PER_INCH = 25.4


class PdfExportError(RuntimeError):
    """Raised when Folio cannot produce a visual PDF export."""


@dataclass(frozen=True)
class PdfPage:
    """Rendered page payload used by the raster-backed PDF exporter."""

    page_number: int
    svg_text: str
    width_mm: float
    height_mm: float


RenderSvg = Callable[[str], Path]


def write_pdf(
    document: Document,
    out_dir: Path,
    *,
    filename: str = _DEFAULT_PDF_NAME,
    pages: Sequence[PdfPage] | None = None,
    render_svg: Callable[[str, Path], Path] | None = None,
) -> Path:
    """Write a visual raster-backed PDF for a rendered Folio document.

    `pages` must contain rendered SVG content for each PDF page. The fallback
    path that receives only a `Document` is intentionally rejected so callers do
    not accidentally produce the old blank placeholder PDF.
    """

    if pages is None:
        raise PdfExportError("PDF export requires rendered page SVG content")

    out_dir.mkdir(parents=True, exist_ok=True)
    target = out_dir / _safe_pdf_name(filename)
    tmp_target = target.with_suffix(f"{target.suffix}.tmp")
    try:
        ordered_pages = tuple(sorted(pages, key=lambda page: page.page_number))
        _write_raster_pdf(ordered_pages, tmp_target, render_svg)
        tmp_target.replace(target)
    except Exception as exc:
        tmp_target.unlink(missing_ok=True)
        if isinstance(exc, PdfExportError):
            raise
        raise PdfExportError(f"Could not export PDF: {exc}") from exc
    return target


def _safe_pdf_name(filename: str) -> str:
    name = Path(filename).name or _DEFAULT_PDF_NAME
    if not name.lower().endswith(".pdf"):
        name = f"{name}.pdf"
    return name


def _write_raster_pdf(
    pages: tuple[PdfPage, ...],
    target: Path,
    render_svg: Callable[[str, Path], Path] | None,
) -> None:
    if not pages:
        raise PdfExportError("PDF export requires at least one page")

    try:
        from PIL import Image  # type: ignore[import-not-found]
    except ImportError as exc:  # pragma: no cover - depends on runtime environment
        raise PdfExportError("PDF export requires Pillow to assemble page images") from exc

    renderer = render_svg or _default_render_svg
    images = []
    with tempfile.TemporaryDirectory(prefix="folio-pdf-") as tmp_dir:
        tmp_path = Path(tmp_dir)
        try:
            for index, page in enumerate(pages, start=1):
                png_path = tmp_path / f"page-{index:04d}.png"
                _render_page_svg(page, png_path, renderer)
                image = Image.open(png_path).convert("RGB")
                images.append(image.copy())
        finally:
            for image in images:
                image.load()

    first, *rest = images
    try:
        target.parent.mkdir(parents=True, exist_ok=True)
        first.save(
            target,
            "PDF",
            save_all=True,
            append_images=rest,
            resolution=float(_PDF_RASTER_DPI),
        )
    finally:
        for image in images:
            image.close()


def _render_page_svg(
    page: PdfPage,
    output_path: Path,
    render_svg: Callable[[str, Path], Path] | None,
) -> Path:
    if render_svg is not None:
        return render_svg(page.svg_text, output_path)
    return _render_svg_preview(
        page.svg_text,
        output_path=output_path,
        viewport=_viewport_for_page(page),
    )


def _viewport_for_page(page: PdfPage) -> tuple[int, int]:
    width = max(1, round((page.width_mm / _MM_PER_INCH) * _PDF_RASTER_DPI))
    height = max(1, round((page.height_mm / _MM_PER_INCH) * _PDF_RASTER_DPI))
    return (width, height)


def _default_render_svg(svg_text: str, output_path: Path) -> Path:
    return _render_svg_preview(svg_text, output_path=output_path)
