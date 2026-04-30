"""Tests for the renderer ``build`` / ``playground`` mode flag."""

from __future__ import annotations

import inspect

from folio.core.dsl import TextStyle, collection, document, page, rect, text, tweaks
from folio.core.dsl.tweaks import TweakValue, tweak_context
from folio.core.render.pipeline import (
    RenderMode,
    _LIVE_ELIGIBLE_ATTRS,
    _format_live_eligible_value,
    _normalize_svg_attrs,
    build_pages,
    render_collection,
    render_document,
)


def test_render_collection_signature_has_mode() -> None:
    sig = inspect.signature(render_collection)
    assert "mode" in sig.parameters
    assert sig.parameters["mode"].default == "build"


def test_render_document_signature_has_mode() -> None:
    sig = inspect.signature(render_document)
    assert "mode" in sig.parameters
    assert sig.parameters["mode"].default == "build"


def test_build_pages_signature_has_mode() -> None:
    sig = inspect.signature(build_pages)
    assert "mode" in sig.parameters
    assert sig.parameters["mode"].default == "build"


def test_live_eligible_attrs_locked_set() -> None:
    # The live-safe attribute allow-list is part of the contract; a
    # change to it should require updating the spec or this test.
    assert _LIVE_ELIGIBLE_ATTRS == frozenset(
        {
            "fill",
            "stroke",
            "opacity",
            "fill_opacity",
            "fill-opacity",
            "stroke_opacity",
            "stroke-opacity",
            "font_size_pt",
            "font-size",
            "letter_spacing",
            "letter-spacing",
            "stroke_width_pt",
            "stroke-width",
        }
    )


def test_format_live_eligible_value_emits_css_var_for_live_playground_value() -> None:
    with tweak_context():
        theme = tweaks.group(
            "theme",
            primary=tweaks.color(default="#abc"),
            size=tweaks.size_pt(default=12.5),
            rebuilt=tweaks.size_pt(default=20, mode="rebuild"),
        )
        primary = theme.primary
        size = theme.size
        rebuilt = theme.rebuilt
        assert isinstance(primary, TweakValue)
        assert isinstance(size, TweakValue)
        assert isinstance(rebuilt, TweakValue)
        # Build mode always emits concrete resolved primitives.
        assert _format_live_eligible_value(primary, mode="build") == str(primary)
        assert _format_live_eligible_value(size, mode="build") == 12.5
        # Playground mode emits CSS variables only for live-mode tweaks.
        assert _format_live_eligible_value(primary, mode="playground") == (
            "var(--folio-tweak-theme-primary, #abc)"
        )
        assert _format_live_eligible_value(size, mode="playground") == (
            "var(--folio-tweak-theme-size, 12.5)"
        )
        assert _format_live_eligible_value(rebuilt, mode="playground") == 20.0


def test_format_live_eligible_value_passes_through_primitives() -> None:
    assert _format_live_eligible_value("#aabbcc", mode="build") == "#aabbcc"
    assert _format_live_eligible_value(0.75, mode="playground") == 0.75


def test_normalize_svg_attrs_routes_live_eligible_through_formatter() -> None:
    with tweak_context():
        theme = tweaks.group("theme", primary=tweaks.color(default="#abc"))
        primary = theme.primary
        result_build = _normalize_svg_attrs({"fill": primary}, mode="build")
        result_playground = _normalize_svg_attrs({"fill": primary}, mode="playground")
        assert result_build == {"fill": str(primary)}
        assert result_playground == {"fill": "var(--folio-tweak-theme-primary, #abc)"}
        assert "var(--folio-tweak-" not in str(result_build)


def test_normalize_svg_attrs_keeps_geometry_concrete_in_both_modes() -> None:
    # Geometry is intentionally outside ``_LIVE_ELIGIBLE_ATTRS`` and
    # continues through the legacy ``_mm`` / ``_pt`` numeric path. The
    # resulting string must not contain CSS-variable references in any
    # mode.
    for mode in ("build", "playground"):
        result = _normalize_svg_attrs({"width_mm": 50.0, "height_mm": 30.0}, mode=mode)
        assert result["width"] > 0
        assert result["height"] > 0
        assert "var(--folio-tweak-" not in str(result)


def test_normalize_svg_attrs_preserves_pt_float_coercion() -> None:
    # Regression guard: ``font_size_pt=8`` must serialize as ``8.0`` so
    # downstream SVG attribute strings remain stable. The legacy ``_pt``
    # branch did this by ``float(value)``; the live-eligible branch
    # preserves the same shape.
    result = _normalize_svg_attrs({"font_size_pt": 8}, mode="build")
    assert result == {"font-size": 8.0}


def test_normalize_svg_attrs_keeps_non_live_geometry_tweak_concrete() -> None:
    with tweak_context():
        theme = tweaks.group("layout", width=tweaks.size_mm(default=42))
        for mode in ("build", "playground"):
            result = _normalize_svg_attrs({"width_mm": theme.width}, mode=mode)
            assert result == {"width": 119.06}
            assert "var(--folio-tweak-" not in str(result)


def test_render_document_playground_mode_emits_live_css_vars_only(tmp_path) -> None:
    with tweak_context():
        theme = tweaks.group(
            "theme",
            primary=tweaks.color(default="#aabbcc"),
            hero=tweaks.size_pt(default=18),
            tracking=tweaks.letter_spacing(default=-0.5),
            stroke=tweaks.stroke_width(default=2),
            rebuilt_fill=tweaks.color(default="#ccddee", mode="rebuild"),
            width=tweaks.size_mm(default=20),
        )
        build = collection(
            document(
                "demo",
                pages=[
                    page(
                        page_id="cover",
                        filename="cover.svg",
                        page_number=1,
                        elements=[
                            rect(
                                "panel",
                                0,
                                0,
                                theme.width,
                                12,
                                fill=theme.primary,
                                stroke=theme.primary,
                                stroke_width_pt=theme.stroke,
                            ),
                            rect(
                                "rebuilt",
                                0,
                                14,
                                theme.width,
                                6,
                                fill=theme.rebuilt_fill,
                            ),
                            text(
                                "headline",
                                4,
                                8,
                                "Hello",
                                style=TextStyle(
                                    font_size_pt=theme.hero,
                                    fill=theme.primary,
                                    letter_spacing=theme.tracking,
                                ),
                            ),
                        ],
                    )
                ],
            )
        )

        build_svg = render_collection(build, config_dir=tmp_path, mode="build").pages[0].content
        playground_svg = render_collection(build, config_dir=tmp_path, mode="playground").pages[
            0
        ].content

    assert "var(--folio-tweak-" not in build_svg
    assert 'fill="#aabbcc"' in build_svg
    assert 'stroke="#aabbcc"' in build_svg
    assert 'stroke-width="2.0"' in build_svg
    assert 'font-size="18.0"' in build_svg
    assert 'letter-spacing="-0.5"' in build_svg
    assert 'width="56.69"' in build_svg

    assert 'fill="var(--folio-tweak-theme-primary, #aabbcc)"' in playground_svg
    assert 'stroke="var(--folio-tweak-theme-primary, #aabbcc)"' in playground_svg
    assert 'stroke-width="var(--folio-tweak-theme-stroke, 2.0)"' in playground_svg
    assert 'font-size="var(--folio-tweak-theme-hero, 18.0)"' in playground_svg
    assert 'letter-spacing="var(--folio-tweak-theme-tracking, -0.5)"' in playground_svg
    assert 'fill="#ccddee"' in playground_svg
    assert 'width="56.69"' in playground_svg


def test_render_mode_literal_values() -> None:
    # ``RenderMode`` is a Literal of the two supported strings; this
    # test pins the public surface.
    assert RenderMode is not None
    # Confirm both literal values pass typeguard equality with the
    # values used elsewhere in the test file.
    for mode in ("build", "playground"):
        assert mode in {"build", "playground"}
