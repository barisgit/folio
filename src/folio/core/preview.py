from __future__ import annotations

import importlib
import re
import shutil
import subprocess
import tempfile
from collections.abc import Callable
from pathlib import Path
from typing import Any

from folio.core.cache import raster_output_path


class PreviewError(Exception):
    """Raised when preview rendering fails."""


def _load_sync_playwright() -> Callable[[], Any] | None:
    try:
        module = importlib.import_module("playwright.sync_api")
    except ImportError:  # pragma: no cover - optional dependency
        return None
    return module.sync_playwright


sync_playwright = _load_sync_playwright()


MM_PER_INCH = 25.4
PX_PER_INCH = 96
PT_PER_INCH = 72
A4_WIDTH_PX = 1191
A4_HEIGHT_PX = 1684
DEFAULT_VIEWPORT = (A4_WIDTH_PX, A4_HEIGHT_PX)
_SVG_TAG_RE = re.compile(r"<svg\b[^>]*>", re.IGNORECASE)
_DIMENSION_RE = re.compile(r'\b(width|height)="([0-9.]+)(mm|pt|px)?"')
_VIEWBOX_RE = re.compile(r'\bviewBox="([0-9.]+)\s+([0-9.]+)\s+([0-9.]+)\s+([0-9.]+)"')


def _mm_to_px(value_mm: float) -> int:
    return max(1, round((value_mm / MM_PER_INCH) * PX_PER_INCH))


def _pt_to_px(value_pt: float) -> int:
    return max(1, round((value_pt / PT_PER_INCH) * PX_PER_INCH))


def _default_viewport(svg_text: str) -> tuple[int, int]:
    svg_tag_match = _SVG_TAG_RE.search(svg_text)
    if svg_tag_match is None:
        return DEFAULT_VIEWPORT

    svg_tag = svg_tag_match.group(0)
    dimensions = {
        name: (float(value), unit or "px")
        for name, value, unit in _DIMENSION_RE.findall(svg_tag)
    }
    if "width" in dimensions and "height" in dimensions:
        width, width_unit = dimensions["width"]
        height, height_unit = dimensions["height"]
        if width_unit == "mm" and height_unit == "mm":
            return (_mm_to_px(width), _mm_to_px(height))
        if width_unit == "pt" and height_unit == "pt":
            return (_pt_to_px(width), _pt_to_px(height))
        if width_unit == "px" and height_unit == "px":
            return (max(1, round(width)), max(1, round(height)))

    match = _VIEWBOX_RE.search(svg_tag)
    if match:
        _, _, width, height = match.groups()
        return (_pt_to_px(float(width)), _pt_to_px(float(height)))

    return DEFAULT_VIEWPORT


def _render_with_playwright(
    svg_text: str,
    *,
    output_path: Path,
    viewport: tuple[int, int],
) -> Path:
    if sync_playwright is None:
        raise PreviewError("Playwright is not installed")

    width, height = viewport
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch()
        page = browser.new_page(
            viewport={"width": width, "height": height}, device_scale_factor=1
        )
        page.set_content(
            f'<html><body style="margin:0;background:white">{svg_text}</body></html>',
            wait_until="load",
        )
        page.locator("svg").screenshot(path=str(output_path))
        browser.close()
    return output_path


def _render_with_cairosvg(
    svg_text: str,
    *,
    output_path: Path,
    viewport: tuple[int, int],
) -> Path:
    cairosvg = importlib.import_module("cairosvg")
    width, height = viewport
    cairosvg.svg2png(
        bytestring=svg_text.encode("utf-8"),
        write_to=str(output_path),
        output_width=width,
        output_height=height,
    )
    return output_path


def _render_with_rsvg_convert(
    svg_text: str,
    *,
    output_path: Path,
    viewport: tuple[int, int],
) -> Path:
    command = shutil.which("rsvg-convert")
    if command is None:
        raise PreviewError("rsvg-convert is not installed")

    width, height = viewport
    subprocess.run(
        [command, "-f", "png", "-w", str(width), "-h", str(height), "-o", str(output_path)],
        input=svg_text,
        text=True,
        capture_output=True,
        check=True,
    )
    return output_path


def _render_with_inkscape(
    svg_text: str,
    *,
    output_path: Path,
    viewport: tuple[int, int],
) -> Path:
    command = shutil.which("inkscape")
    if command is None:
        raise PreviewError("Inkscape is not installed")

    width, height = viewport
    with tempfile.TemporaryDirectory(prefix="folio-preview-") as tmp_dir:
        svg_path = Path(tmp_dir) / "preview.svg"
        svg_path.write_text(svg_text, encoding="utf-8")
        subprocess.run(
            [
                command,
                str(svg_path),
                f"--export-filename={output_path}",
                "--export-type=png",
                f"--export-width={width}",
                f"--export-height={height}",
            ],
            capture_output=True,
            text=True,
            check=True,
        )
    return output_path


def _render_svg_preview(
    svg_text: str,
    *,
    output_path: Path,
    viewport: tuple[int, int] | None = None,
) -> Path:
    resolved_viewport = viewport or _default_viewport(svg_text)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    renderers = [
        ("Playwright", _render_with_playwright),
        ("CairoSVG", _render_with_cairosvg),
        ("rsvg-convert", _render_with_rsvg_convert),
        ("Inkscape", _render_with_inkscape),
    ]
    errors: list[str] = []
    for name, renderer in renderers:
        try:
            return renderer(svg_text, output_path=output_path, viewport=resolved_viewport)
        except Exception as exc:  # pragma: no cover - exercised via monkeypatch in tests
            errors.append(f"{name}: {exc}")

    attempts = "; ".join(errors)
    raise PreviewError(
        "Could not rasterize SVG. Tried Playwright, CairoSVG, rsvg-convert, and Inkscape. "
        f"Failures: {attempts}"
    )


def render_preview_file(
    svg_path: Path,
    *,
    output_path: Path | None = None,
    viewport: tuple[int, int] | None = None,
) -> Path:
    resolved_svg = svg_path.expanduser().resolve()
    target = (output_path or resolved_svg.with_suffix(".png")).expanduser().resolve()
    return _render_svg_preview(
        resolved_svg.read_text(encoding="utf-8"),
        output_path=target,
        viewport=viewport,
    )


def render_raster(
    svg_path: Path,
    *,
    spec_path: Path,
    page_number: int,
    viewport: tuple[int, int] | None = None,
) -> Path:
    return render_preview_file(
        svg_path,
        output_path=raster_output_path(spec_path, page_number),
        viewport=viewport,
    )


def render_preview(
    svg_path: Path,
    *,
    spec_path: Path,
    page_number: int,
    viewport: tuple[int, int] | None = None,
) -> Path:
    return render_raster(
        svg_path,
        spec_path=spec_path,
        page_number=page_number,
        viewport=viewport,
    )
