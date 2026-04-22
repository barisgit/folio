from __future__ import annotations

from pathlib import Path

import pytest

import folio.preview as preview

SVG = (
    '<svg xmlns="http://www.w3.org/2000/svg" '
    'width="99mm" height="210mm" viewBox="0 0 280.63 595.28"></svg>'
)


def test_default_viewport_uses_svg_dimensions() -> None:
    assert preview._default_viewport(SVG) == (374, 794)



def test_render_svg_preview_falls_back_between_renderers(
    tmp_path: Path,
    monkeypatch,
) -> None:
    output_path = tmp_path / "preview.png"
    calls: list[str] = []

    def fail_playwright(svg_text: str, *, output_path: Path, viewport: tuple[int, int]) -> Path:
        calls.append(f"playwright:{viewport}")
        raise preview.PreviewError("missing browser")

    def succeed_cairosvg(svg_text: str, *, output_path: Path, viewport: tuple[int, int]) -> Path:
        calls.append(f"cairosvg:{viewport}")
        output_path.write_bytes(b"PNG")
        return output_path

    monkeypatch.setattr(preview, "_render_with_playwright", fail_playwright)
    monkeypatch.setattr(preview, "_render_with_cairosvg", succeed_cairosvg)
    monkeypatch.setattr(
        preview,
        "_render_with_rsvg_convert",
        lambda *args, **kwargs: pytest.fail("unexpected rsvg-convert call"),
    )
    monkeypatch.setattr(
        preview,
        "_render_with_inkscape",
        lambda *args, **kwargs: pytest.fail("unexpected Inkscape call"),
    )

    result = preview._render_svg_preview(SVG, output_path=output_path)

    assert result == output_path
    assert output_path.exists()
    assert calls == ["playwright:(374, 794)", "cairosvg:(374, 794)"]
