from __future__ import annotations

from pathlib import Path

from folio.cache import preview_output_path


class PreviewError(Exception):
    """Raised when preview rendering fails."""


try:
    from playwright.sync_api import sync_playwright
except ImportError:  # pragma: no cover - optional dependency
    sync_playwright = None


SCALE = 2
A4_WIDTH_PX = 1191
A4_HEIGHT_PX = 1684
DEFAULT_VIEWPORT = (A4_WIDTH_PX, A4_HEIGHT_PX)


def _render_svg_preview(
    svg_text: str,
    *,
    output_path: Path,
    viewport: tuple[int, int] | None = None,
) -> Path:
    if sync_playwright is None:
        raise PreviewError(
            "Playwright is not installed. Install it and browser binaries to use 'folio preview'."
        )

    width, height = viewport or DEFAULT_VIEWPORT
    output_path.parent.mkdir(parents=True, exist_ok=True)

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


def render_preview(
    svg_path: Path,
    *,
    spec_path: Path,
    page_number: int,
    viewport: tuple[int, int] | None = None,
) -> Path:
    return render_preview_file(
        svg_path,
        output_path=preview_output_path(spec_path, page_number),
        viewport=viewport,
    )
