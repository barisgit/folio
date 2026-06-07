from __future__ import annotations

from pathlib import Path

import pytest

import folio.core.preview as preview

SVG = (
    '<svg xmlns="http://www.w3.org/2000/svg" '
    'width="99mm" height="210mm" viewBox="0 0 280.63 595.28"></svg>'
)


def test_default_viewport_uses_svg_dimensions() -> None:
    assert preview._default_viewport(SVG) == (374, 794)


def test_default_viewport_ignores_nested_dimensions() -> None:
    svg = (
        '<svg xmlns="http://www.w3.org/2000/svg" '
        'width="240mm" height="135mm" viewBox="0 0 680.31 382.68">'
        '<defs><filter width="140%" height="140%"></filter></defs>'
        '<rect width="1" height="31" />'
        "</svg>"
    )

    assert preview._default_viewport(svg) == (907, 510)


def test_default_viewport_uses_root_viewbox_when_dimensions_are_missing() -> None:
    svg = (
        '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 1920 1080">'
        '<rect width="1" height="31" />'
        "</svg>"
    )

    assert preview._default_viewport(svg) == (2560, 1440)


def test_render_svg_preview_defaults_to_playwright(
    tmp_path: Path,
    monkeypatch,
) -> None:
    output_path = tmp_path / "preview.png"
    calls: list[str] = []

    def succeed_playwright(
        svg_text: str, *, output_path: Path, viewport: tuple[int, int], background: str
    ) -> Path:
        calls.append(f"playwright:{viewport}:{background}")
        output_path.write_bytes(b"PNG")
        return output_path

    monkeypatch.setattr(preview, "_render_with_playwright", succeed_playwright)
    for name in ("_render_with_cairosvg", "_render_with_rsvg_convert", "_render_with_inkscape"):
        monkeypatch.setattr(
            preview,
            name,
            lambda *args, _name=name, **kwargs: pytest.fail(f"unexpected {_name} call"),
        )

    result = preview._render_svg_preview(SVG, output_path=output_path)

    assert result == output_path
    assert output_path.exists()
    # Default renderer is playwright, default background is white (opaque).
    assert calls == ["playwright:(374, 794):white"]


def test_render_svg_preview_does_not_silently_fall_back(
    tmp_path: Path,
    monkeypatch,
) -> None:
    output_path = tmp_path / "preview.png"

    def fail_playwright(
        svg_text: str, *, output_path: Path, viewport: tuple[int, int], background: str
    ) -> Path:
        raise preview.PreviewError(preview.CHROMIUM_UNAVAILABLE_MESSAGE)

    monkeypatch.setattr(preview, "_render_with_playwright", fail_playwright)
    for name in ("_render_with_cairosvg", "_render_with_rsvg_convert", "_render_with_inkscape"):
        monkeypatch.setattr(
            preview,
            name,
            lambda *args, **kwargs: pytest.fail("reduced-fidelity renderer used as fallback"),
        )

    with pytest.raises(preview.PreviewError, match="playwright install chromium"):
        preview._render_svg_preview(SVG, output_path=output_path)


def test_render_svg_preview_explicit_renderer_selection(
    tmp_path: Path,
    monkeypatch,
) -> None:
    output_path = tmp_path / "preview.png"
    calls: list[str] = []

    def succeed_rsvg(
        svg_text: str, *, output_path: Path, viewport: tuple[int, int], background: str
    ) -> Path:
        calls.append(f"rsvg:{viewport}:{background}")
        output_path.write_bytes(b"PNG")
        return output_path

    monkeypatch.setattr(
        preview,
        "_render_with_playwright",
        lambda *args, **kwargs: pytest.fail("playwright used despite explicit renderer"),
    )
    monkeypatch.setattr(preview, "_render_with_rsvg_convert", succeed_rsvg)

    result = preview._render_svg_preview(
        SVG, output_path=output_path, renderer="rsvg", background="transparent"
    )

    assert result == output_path
    assert calls == ["rsvg:(374, 794):transparent"]


def test_render_svg_preview_rejects_unknown_renderer(tmp_path: Path) -> None:
    with pytest.raises(preview.PreviewError, match="Unknown renderer"):
        preview._render_svg_preview(
            SVG, output_path=tmp_path / "preview.png", renderer="nope"
        )


def test_force_root_pixel_size_overrides_intrinsic_dimensions() -> None:
    sized = preview._force_root_pixel_size(SVG, 1465, 1465)

    assert 'width="1465px"' in sized
    assert 'height="1465px"' in sized
    assert "99mm" not in sized
    assert "210mm" not in sized
    # viewBox is preserved so content scales to fill the requested size.
    assert 'viewBox="0 0 280.63 595.28"' in sized
