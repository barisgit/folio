from __future__ import annotations

import re
from pathlib import Path

import pytest

from folio.dsl import (
    block,
    clip_path,
    component_transfer,
    filter_,
    func_a,
    gaussian_blur,
    group,
    linear_gradient,
    markup,
    merge,
    merge_node,
    multiline,
    offset,
    page,
    rect,
    render,
    rule,
    span,
    stop,
    text,
    tokens,
    triangle,
    tspan,
)
from folio.dsl.loader import DslError, load_dsl_module
from folio.dsl.renderer import (
    RenderError,
    ValidationWarning,
    build_pages,
    render_document,
    validate_document,
)

SPEC = """from folio.dsl import group, image, page, rect, render, text, tokens

document = render(
    page(
        page_id="cover",
        filename="cover.svg",
        page_number=1,
        elements=[
            group(
                "cover_group",
                "Cover",
                [
                    rect("bg", 0, 0, 210, 297, fill=tokens.INK),
                    image("logo", "logo.png", 10, 10, 8, 8),
                    text("headline", 16, 24, "Hello DSL", size_pt=18, fill=tokens.WHITE),
                ],
            ),
        ],
    ),
)
"""


def test_load_dsl_module_and_build_pages(tmp_path: Path) -> None:
    asset = tmp_path / "logo.png"
    asset.write_bytes(b"\x89PNG\r\n\x1a\n")
    spec_path = tmp_path / "spec.py"
    spec_path.write_text(SPEC, encoding="utf-8")

    module = load_dsl_module(spec_path)
    result = build_pages(module, config_dir=spec_path.parent)

    assert result.config_hash
    assert [page.filename for page in result.pages] == ["cover.svg"]

    content = result.pages[0].content
    assert 'data-page-number="1"' in content
    assert 'data-page-id="cover"' in content
    assert 'id="headline"' in content
    assert "Hello DSL" in content
    assert "data:image/png;base64," in content


def test_load_dsl_module_reports_syntax_errors(tmp_path: Path) -> None:
    spec_path = tmp_path / "broken.py"
    spec_path.write_text("def broken(:\n    pass\n", encoding="utf-8")

    with pytest.raises(DslError, match="Syntax error"):
        load_dsl_module(spec_path)


def test_render_document_generates_ids_for_unset_elements(tmp_path: Path) -> None:
    document = render(
        page(
            page_id="cover",
            filename="cover.svg",
            page_number=1,
            elements=[
                rect(None, 0, 0, 10, 10, fill=tokens.INK),
                text(None, 5, 5, "Auto ID", size_pt=12),
            ],
        )
    )

    result = render_document(document, config_dir=tmp_path)
    content = result.pages[0].content

    assert re.search(r'id="rect_\d+"', content)
    assert re.search(r'id="text_\d+"', content)


def test_validate_document_rejects_child_id_matching_page_root() -> None:
    document = render(
        page(
            page_id="cover",
            filename="cover.svg",
            page_number=1,
            elements=[
                rect("cover", 0, 0, 10, 10, fill=tokens.INK),
            ],
        )
    )

    with pytest.raises(RenderError, match="Duplicate element id: cover"):
        validate_document(document)


def test_render_document_normalizes_svg_attrs(tmp_path: Path) -> None:
    document = render(
        page(
            page_id="cover",
            filename="cover.svg",
            page_number=1,
            elements=[
                rect(
                    "panel",
                    10,
                    20,
                    30,
                    40,
                    fill=tokens.WHITE,
                    rx_mm=2.5,
                    ry_mm=2.5,
                    stroke=tokens.INK,
                    stroke_width_pt=0.3,
                    fill_opacity=0.7,
                    clip_path="url(#panelClip)",
                ),
            ],
        )
    )

    content = render_document(document, config_dir=tmp_path).pages[0].content

    assert 'rx="7.09"' in content
    assert 'ry="7.09"' in content
    assert 'stroke-width="0.3"' in content
    assert 'fill-opacity="0.7"' in content
    assert 'clip-path="url(#panelClip)"' in content


def test_public_render_builder_survives_renderer_import_order() -> None:
    from folio.dsl import render as render_builder

    assert callable(render_builder)


def test_page_group_and_defs_accept_variadic_children(tmp_path: Path) -> None:
    document = render(
        page(
            group(
                "cover_group",
                "Cover",
                rect("bg", 0, 0, 20, 20, fill=tokens.INK),
                text("headline", 5, 5, "Hello DSL", size_pt=12, fill=tokens.WHITE),
            ),
            page_id="cover",
            filename="cover.svg",
            page_number=1,
            defs=[
                linear_gradient(
                    "panel_gradient",
                    stop("panel_gradient_stop_1", offset="0%", stop_color=tokens.INK),
                    stop("panel_gradient_stop_2", offset="100%", stop_color=tokens.LINE),
                    x1="0",
                    y1="0",
                    x2="1",
                    y2="1",
                ),
                filter_(
                    "shadow_filter",
                    gaussian_blur("shadow_blur", in_="SourceAlpha", stdDeviation="4"),
                ),
                clip_path(
                    "panel_clip",
                    rect("panel_clip_rect", 0, 0, 20, 20, fill="none"),
                ),
            ],
        )
    )

    content = render_document(document, config_dir=tmp_path).pages[0].content

    assert 'id="cover_group"' in content
    assert 'id="headline"' in content
    assert 'id="panel_gradient"' in content
    assert 'id="shadow_blur"' in content
    assert 'id="panel_clip_rect"' in content


def test_page_rejects_mixed_positional_and_keyword_elements() -> None:
    with pytest.raises(TypeError, match="either positional elements or elements"):
        page(
            rect("bg", 0, 0, 10, 10, fill=tokens.INK),
            page_id="cover",
            filename="cover.svg",
            page_number=1,
            elements=[text("headline", 5, 5, "Hello", size_pt=12)],
        )



def test_block_and_callable_style_helpers_render(tmp_path: Path) -> None:
    card = block("card", at=(10, 20))
    document = render(
        page(
            tokens.STYLES.hero(
                "headline",
                5,
                6,
                [
                    "Hello ",
                    tokens.STYLES.kicker.span(
                        "headline_accent",
                        "world",
                        fill=tokens.ACCENT_DARK,
                        letter_spacing=0,
                    ),
                ],
                size_pt=20,
                fill=tokens.INK,
                letter_spacing=-0.1,
            ),
            multiline(
                "copy",
                5,
                14,
                ["Line 1", "Line 2"],
                line_step_mm=4,
                style=tokens.STYLES.body,
                fill=tokens.INK_2,
            ),
            rule("copy_sep", 5, 23, 20, fill=tokens.LINE, opacity=0.4),
            tokens.STYLES.body.multiline(
                "copy_style",
                5,
                28,
                ["Line 3", "Line 4"],
                line_step_mm=4,
                fill=tokens.INK_2,
            ),
            card.layer(
                "Card",
                card.rect(
                    "panel",
                    0,
                    0,
                    30,
                    18,
                    fill=tokens.WHITE,
                    stroke=tokens.LINE,
                    stroke_width=0.3,
                ),
                card.text(
                    "title",
                    3,
                    4,
                    "Scoped title",
                    style=tokens.STYLES.title,
                ),
                card.multiline(
                    "body",
                    3,
                    9,
                    ["Line A", "Line B"],
                    line_step_mm=4,
                    style=tokens.STYLES.body,
                ),
                card.rule("sep", 0, 16, 30, fill=tokens.LINE, opacity=0.5),
            ),
            page_id="cover",
            filename="cover.svg",
            page_number=1,
        )
    )

    content = render_document(document, config_dir=tmp_path).pages[0].content

    assert 'id="headline"' in content
    assert 'id="headline_accent"' in content
    assert 'fill="#8f7223"' in content
    assert 'letter-spacing="0"' in content
    assert 'id="copy_line_2"' in content
    assert 'id="copy_sep"' in content
    assert 'id="copy_style_line_2"' in content
    assert 'id="card_group"' in content
    assert 'id="card_panel"' in content
    assert 'id="card_title"' in content
    assert re.search(r'<text id="card_title"[^>]* x="36\.85" y="68\.03"', content)
    assert 'id="card_body_line_1"' in content
    assert 'id="card_body_line_2"' in content
    assert 'id="card_sep"' in content



def test_render_document_supports_structured_text_content(tmp_path: Path) -> None:
    document = render(
        page(
            page_id="cover",
            filename="cover.svg",
            page_number=1,
            elements=[
                text(
                    "headline",
                    10,
                    20,
                    [
                        "Hello ",
                        span(
                            "headline_accent",
                            "world",
                            style=tokens.STYLES.kicker,
                            fill=tokens.ACCENT,
                            letter_spacing=None,
                        ),
                        " & beyond",
                    ],
                    style=tokens.STYLES.body,
                    size_pt=12,
                    fill=tokens.INK,
                ),
                text(
                    "copy",
                    10,
                    30,
                    [
                        tspan("copy_line_1", "Line 1", x_mm=10, y_mm=30),
                        tspan(
                            "copy_line_2",
                            [
                                "Line ",
                                tspan("copy_line_2_accent", "2", fill=tokens.BLUE_GLOW),
                            ],
                            x_mm=10,
                            y_mm=35,
                        ),
                    ],
                    style=tokens.STYLES.body,
                    size_pt=10,
                    fill=tokens.INK_2,
                ),
            ],
        )
    )

    content = render_document(document, config_dir=tmp_path).pages[0].content

    assert 'id="headline_accent"' in content
    assert (
        '<tspan id="headline_accent" font-size="8.0" '
        'font-weight="700" fill="#c8a24a">world</tspan>'
    ) in content
    assert 'Hello ' in content
    assert '&amp; beyond' in content
    assert 'id="copy_line_1"' in content
    assert 'id="copy_line_2"' in content
    assert 'id="copy_line_2_accent"' in content


def test_text_style_kwargs_override_preset_defaults(tmp_path: Path) -> None:
    document = render(
        page(
            page_id="cover",
            filename="cover.svg",
            page_number=1,
            elements=[
                text(
                    "headline",
                    10,
                    20,
                    [
                        "Preset ",
                        span(
                            "headline_accent",
                            "override",
                            style=tokens.STYLES.kicker,
                            fill=tokens.ACCENT_DARK,
                            letter_spacing=0,
                        ),
                    ],
                    style=tokens.STYLES.hero,
                    size_pt=22,
                    weight=600,
                    fill=tokens.ACCENT,
                    letter_spacing=-0.2,
                )
            ],
        )
    )

    content = render_document(document, config_dir=tmp_path).pages[0].content

    assert '<text id="headline"' in content
    assert 'font-size="22.0"' in content
    assert 'font-weight="600"' in content
    assert 'fill="#c8a24a"' in content
    assert 'letter-spacing="-0.2"' in content
    assert (
        '<tspan id="headline_accent" font-size="8.0" font-weight="700" '
        'fill="#8f7223" letter-spacing="0">override</tspan>'
    ) in content


def test_validate_document_rejects_duplicate_text_span_id() -> None:
    document = render(
        page(
            page_id="cover",
            filename="cover.svg",
            page_number=1,
            elements=[
                text(
                    "headline",
                    10,
                    20,
                    ["Hello ", tspan("headline", "world")],
                    size_pt=12,
                )
            ],
        )
    )

    with pytest.raises(RenderError, match="Duplicate element id: headline"):
        validate_document(document)


def test_render_document_supports_structured_defs(tmp_path: Path) -> None:
    document = render(
        page(
            page_id="cover",
            filename="cover.svg",
            page_number=1,
            defs=[
                linear_gradient(
                    "panel_gradient",
                    [
                        stop("panel_gradient_stop_1", offset="0%", stop_color=tokens.INK),
                        stop("panel_gradient_stop_2", offset="100%", stop_color=tokens.LINE),
                    ],
                    x1="0",
                    y1="0",
                    x2="1",
                    y2="1",
                ),
                filter_(
                    "shadow_filter",
                    [
                        gaussian_blur("shadow_blur", in_="SourceAlpha", stdDeviation="4")
                    ],
                ),
                clip_path(
                    "panel_clip",
                    [rect("panel_clip_rect", 0, 0, 20, 20, fill="none")],
                ),
            ],
            elements=[
                rect(
                    "panel",
                    0,
                    0,
                    20,
                    20,
                    fill="url(#panel_gradient)",
                    clip_path="url(#panel_clip)",
                    filter="url(#shadow_filter)",
                )
            ],
        )
    )

    content = render_document(document, config_dir=tmp_path).pages[0].content

    assert "<defs>" in content
    assert 'id="panel_gradient"' in content
    assert 'id="panel_gradient_stop_1"' in content
    assert 'stop-color="#0a1628"' in content
    assert 'id="shadow_filter"' in content
    assert 'id="shadow_blur"' in content
    assert 'in="SourceAlpha"' in content
    assert 'id="panel_clip"' in content
    assert 'id="panel_clip_rect"' in content


def test_text_style_markup_and_triangle_helpers_render(tmp_path: Path) -> None:
    document = render(
        page(
            page_id="cover",
            filename="cover.svg",
            page_number=1,
            defs=[
                filter_(
                    "shadow_filter",
                    [
                        gaussian_blur("shadow_blur", in_="SourceAlpha", stdDeviation="4"),
                        offset("shadow_offset", dy="2"),
                        component_transfer(
                            "shadow_alpha",
                            [func_a("shadow_alpha_curve", type="linear", slope="0.8")],
                        ),
                        merge(
                            "shadow_merge",
                            [
                                merge_node("shadow_merge_shadow"),
                                merge_node("shadow_merge_graphic", in_="SourceGraphic"),
                            ],
                        ),
                    ],
                )
            ],
            elements=[
                text(
                    "headline",
                    10,
                    20,
                    ["Use ", markup("&amp;"), " escape hatch"],
                    style=tokens.STYLES.kicker,
                    size_pt=12,
                    fill=tokens.INK,
                ),
                triangle(
                    "arrow",
                    cx_mm=22.5,
                    cy_mm=32,
                    size_mm=4,
                    width_mm=5,
                    height_mm=4,
                    fill=tokens.ACCENT,
                ),
            ],
        )
    )

    content = render_document(document, config_dir=tmp_path).pages[0].content

    assert 'id="shadow_offset"' in content
    assert 'id="shadow_alpha_curve"' in content
    assert 'id="shadow_merge_graphic"' in content
    assert '>Use &amp; escape hatch</text>' in content
    assert 'id="arrow"' in content
    assert '<path id="arrow"' in content


def test_text_raw_is_replaced_by_markup_builder() -> None:
    with pytest.raises(TypeError, match="use markup"):
        text("headline", 10, 20, "Hello", raw=True)

    with pytest.raises(TypeError, match="use markup"):
        tspan("headline_accent", "world", raw=True)


def test_validate_document_warns_on_non_token_hex_colors() -> None:
    document = render(
        page(
            page_id="cover",
            filename="cover.svg",
            page_number=1,
            elements=[rect("panel", 0, 0, 10, 10, fill="#123456")],
        )
    )

    with pytest.warns(ValidationWarning, match="#123456"):
        validate_document(document)
