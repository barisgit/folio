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


CHROMIUM_UNAVAILABLE_MESSAGE = (
    "Chromium renderer unavailable. Run `playwright install chromium`, or select a "
    "reduced-fidelity renderer explicitly (renderer='rsvg'|'cairosvg'|'inkscape'); "
    "note these do not render curved text (`textPath`) or all filters."
)

DEFAULT_BACKGROUND = "white"
TRANSPARENT_BACKGROUND = "transparent"


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


def _force_root_pixel_size(svg_text: str, width: int, height: int) -> str:
    """Force the root ``<svg>`` element to an explicit pixel size.

    Element screenshots capture the SVG at its intrinsic CSS size, so a root of
    ``width="124mm"`` always rasterizes at ~469px regardless of the requested
    viewport. Rewriting the root width/height to the requested px makes the
    element's intrinsic size equal the target raster size. The ``viewBox`` is
    left untouched so the content scales to fill.
    """
    match = _SVG_TAG_RE.search(svg_text)
    if match is None:
        return svg_text
    tag = match.group(0)
    stripped = _DIMENSION_RE.sub("", tag)
    # Insert explicit px width/height right after the opening "<svg".
    sized_tag = f'<svg width="{width}px" height="{height}px"' + stripped[len("<svg") :]
    return svg_text[: match.start()] + sized_tag + svg_text[match.end() :]


def _default_viewport(svg_text: str) -> tuple[int, int]:
    svg_tag_match = _SVG_TAG_RE.search(svg_text)
    if svg_tag_match is None:
        return DEFAULT_VIEWPORT

    svg_tag = svg_tag_match.group(0)
    dimensions = {
        name: (float(value), unit or "px") for name, value, unit in _DIMENSION_RE.findall(svg_tag)
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
    background: str = DEFAULT_BACKGROUND,
) -> Path:
    if sync_playwright is None:
        raise PreviewError(CHROMIUM_UNAVAILABLE_MESSAGE)

    width, height = viewport
    # Bug #1: force the root size so the element screenshot matches the request.
    sized_svg = _force_root_pixel_size(svg_text, width, height)
    # Bug #2: honor transparency instead of always baking onto white.
    transparent = background == TRANSPARENT_BACKGROUND
    body_background = "transparent" if transparent else background
    with sync_playwright() as playwright:
        try:
            browser = playwright.chromium.launch()
        except Exception as exc:  # pragma: no cover - depends on local browser install
            raise PreviewError(CHROMIUM_UNAVAILABLE_MESSAGE) from exc
        try:
            page = browser.new_page(
                viewport={"width": width, "height": height}, device_scale_factor=1
            )
            page.set_content(
                f'<html><body style="margin:0;background:{body_background}">'
                f"{sized_svg}</body></html>",
                wait_until="load",
            )
            page.locator("svg").screenshot(
                path=str(output_path), omit_background=transparent
            )
        finally:
            browser.close()
    return output_path


def _render_with_cairosvg(
    svg_text: str,
    *,
    output_path: Path,
    viewport: tuple[int, int],
    background: str = DEFAULT_BACKGROUND,
) -> Path:
    cairosvg = importlib.import_module("cairosvg")
    width, height = viewport
    background_color = None if background == TRANSPARENT_BACKGROUND else background
    cairosvg.svg2png(
        bytestring=svg_text.encode("utf-8"),
        write_to=str(output_path),
        output_width=width,
        output_height=height,
        background_color=background_color,
    )
    return output_path


def _render_with_rsvg_convert(
    svg_text: str,
    *,
    output_path: Path,
    viewport: tuple[int, int],
    background: str = DEFAULT_BACKGROUND,
) -> Path:
    command = shutil.which("rsvg-convert")
    if command is None:
        raise PreviewError("rsvg-convert is not installed")

    width, height = viewport
    args = [command, "-f", "png", "-w", str(width), "-h", str(height)]
    if background != TRANSPARENT_BACKGROUND:
        args += ["-b", background]
    args += ["-o", str(output_path)]
    subprocess.run(
        args,
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
    background: str = DEFAULT_BACKGROUND,
) -> Path:
    command = shutil.which("inkscape")
    if command is None:
        raise PreviewError("Inkscape is not installed")

    width, height = viewport
    transparent = background == TRANSPARENT_BACKGROUND
    with tempfile.TemporaryDirectory(prefix="folio-preview-") as tmp_dir:
        svg_path = Path(tmp_dir) / "preview.svg"
        svg_path.write_text(svg_text, encoding="utf-8")
        args = [
            command,
            str(svg_path),
            f"--export-filename={output_path}",
            "--export-type=png",
            f"--export-width={width}",
            f"--export-height={height}",
            f"--export-background-opacity={0 if transparent else 1}",
        ]
        if not transparent:
            args.append(f"--export-background={background}")
        subprocess.run(
            args,
            capture_output=True,
            text=True,
            check=True,
        )
    return output_path


DEFAULT_RENDERER = "playwright"


def _render_svg_preview(
    svg_text: str,
    *,
    output_path: Path,
    viewport: tuple[int, int] | None = None,
    renderer: str | None = None,
    background: str = DEFAULT_BACKGROUND,
) -> Path:
    resolved_viewport = viewport or _default_viewport(svg_text)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    # Built per-call so monkeypatched renderers in tests resolve correctly.
    renderers = {
        "playwright": _render_with_playwright,
        "cairosvg": _render_with_cairosvg,
        "rsvg": _render_with_rsvg_convert,
        "inkscape": _render_with_inkscape,
    }
    selected = (renderer or DEFAULT_RENDERER).lower()
    if selected not in renderers:
        available = ", ".join(renderers)
        raise PreviewError(f"Unknown renderer {renderer!r}. Choose one of: {available}.")

    # Playwright/Chromium is the single canonical default. There is no silent
    # downgrade: an unavailable Chromium fails loudly (see
    # CHROMIUM_UNAVAILABLE_MESSAGE), and the lower-fidelity engines are only
    # used when explicitly requested via ``renderer=``.
    render = renderers[selected]
    return render(
        svg_text,
        output_path=output_path,
        viewport=resolved_viewport,
        background=background,
    )


def render_preview_file(
    svg_path: Path,
    *,
    output_path: Path | None = None,
    viewport: tuple[int, int] | None = None,
    renderer: str | None = None,
    background: str = DEFAULT_BACKGROUND,
) -> Path:
    resolved_svg = svg_path.expanduser().resolve()
    target = (output_path or resolved_svg.with_suffix(".png")).expanduser().resolve()
    return _render_svg_preview(
        resolved_svg.read_text(encoding="utf-8"),
        output_path=target,
        viewport=viewport,
        renderer=renderer,
        background=background,
    )


def render_raster(
    svg_path: Path,
    *,
    spec_path: Path,
    page_number: int,
    viewport: tuple[int, int] | None = None,
    renderer: str | None = None,
    background: str = DEFAULT_BACKGROUND,
) -> Path:
    return render_preview_file(
        svg_path,
        output_path=raster_output_path(spec_path, page_number),
        viewport=viewport,
        renderer=renderer,
        background=background,
    )


def render_preview(
    svg_path: Path,
    *,
    spec_path: Path,
    page_number: int,
    viewport: tuple[int, int] | None = None,
    renderer: str | None = None,
    background: str = DEFAULT_BACKGROUND,
) -> Path:
    return render_raster(
        svg_path,
        spec_path=spec_path,
        page_number=page_number,
        viewport=viewport,
        renderer=renderer,
        background=background,
    )
