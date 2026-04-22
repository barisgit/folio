from __future__ import annotations

import re
import warnings
from pathlib import Path
from typing import cast

import pytest

from folio.dsl import (
    TextLayoutWarning,
    block,
    clip_path,
    component_transfer,
    drop_shadow,
    ellipse,
    filter_,
    func_a,
    gaussian_blur,
    grain,
    group,
    image,
    linear_gradient,
    linear_gradient_stops,
    markup,
    measure_text,
    measure_wrapped_text,
    merge,
    merge_node,
    multiline,
    offset,
    page,
    polygon,
    polyline,
    qr,
    rect,
    render,
    rule,
    span,
    stop,
    text,
    tokens,
    transform_builder,
    triangle,
    tspan,
    wrapped_text,
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



def test_page_size_can_be_overridden(tmp_path: Path) -> None:
    document = render(
        page(
            rect("bg", 0, 0, 99, 210, fill=tokens.INK),
            page_id="dl",
            filename="dl.svg",
            page_number=1,
            width_mm=tokens.DL[0],
            height_mm=tokens.DL[1],
        )
    )

    content = render_document(document, config_dir=tmp_path).pages[0].content

    assert 'width="99mm" height="210mm"' in content
    assert 'viewBox="0 0 280.63 595.28"' in content



def test_render_document_supports_shape_primitives_and_path_builder(tmp_path: Path) -> None:
    card = block("card", at=(40, 50))
    builder = card.path_builder().move_to(0, 0).line_to(10, 0).quad_to(15, 5, 10, 10).close()
    document = render(
        page(
            page_id="cover",
            filename="cover.svg",
            page_number=1,
            elements=[
                ellipse("oval", 20, 30, 5, 7, fill=tokens.ACCENT),
                polygon("triangle_poly", [(0, 0), (10, 0), (5, 10)], fill=tokens.INK),
                polyline(
                    "path_line",
                    [(0, 12), (5, 16), (10, 12)],
                    fill="none",
                    stroke=tokens.INK,
                ),
                card.polygon(
                    "scoped_poly",
                    [(0, 0), (8, 0), (8, 8), (0, 8)],
                    fill=tokens.SOFT,
                ),
                card.path("wave", builder, stroke=tokens.ACCENT, fill="none"),
            ],
        )
    )

    content = render_document(document, config_dir=tmp_path).pages[0].content

    assert '<ellipse id="oval"' in content
    assert 'rx="14.17"' in content
    assert 'ry="19.84"' in content
    assert '<polygon id="triangle_poly" points="0.0,0.0 28.35,0.0 14.17,28.35"' in content
    assert '<polyline id="path_line" points="0.0,34.02 14.17,45.35 28.35,34.02"' in content
    assert 'id="card_scoped_poly"' in content
    assert (
        '<path id="card_wave" d="M113.39 141.73 L141.73 141.73 '
        'Q155.91 155.91 141.73 170.08 Z"'
        in content
    )



def test_transform_builder_serializes_mm_aware_group_transforms(tmp_path: Path) -> None:
    card = block("card", at=(20, 40))
    document = render(
        page(
            page_id="cover",
            filename="cover.svg",
            page_number=1,
            elements=[
                group(
                    "rotated_group",
                    "Rotated",
                    rect("panel", 0, 0, 20, 10, fill=tokens.SOFT),
                    transform=transform_builder().translate(10, 5).rotate(15, cx_mm=20, cy_mm=10),
                ),
                card.layer(
                    "Card",
                    card.rect("panel", 0, 0, 10, 10, fill=tokens.INK),
                    transform=card.transform_builder().rotate(30, cx_mm=5, cy_mm=5).scale(1.2),
                ),
            ],
        )
    )

    content = render_document(document, config_dir=tmp_path).pages[0].content

    assert 'transform="translate(28.35 14.17) rotate(15 56.69 28.35)"' in content
    assert 'transform="rotate(30 70.87 127.56) scale(1.2)"' in content



def test_qr_renders_compact_paths_and_block_helper(tmp_path: Path) -> None:
    card = block("card", at=(20, 40))
    document = render(
        page(
            page_id="cover",
            filename="cover.svg",
            page_number=1,
            elements=[
                qr(
                    "code",
                    10,
                    20,
                    "https://example.com/folio",
                    size_mm=29,
                    background_fill=tokens.WHITE,
                ),
                card.qr(
                    "mini",
                    0,
                    0,
                    b"folio",
                    size_mm=21,
                    ecc="H",
                    border_modules=2,
                    fill=tokens.ACCENT,
                ),
            ],
        )
    )

    content = render_document(document, config_dir=tmp_path).pages[0].content

    assert '<g id="code"' in content
    assert '<rect id="code_bg"' in content
    assert '<path id="code_fg" d="M' in content
    assert '<g id="card_mini"' in content
    assert '<path id="card_mini_fg" d="M' in content
    assert 'shape-rendering="crispEdges"' in content
    assert content.count("<rect") == 1



def test_qr_rejects_invalid_arguments() -> None:
    with pytest.raises(TypeError, match=r"qr\(\) data must be a string or bytes"):
        qr("code", 0, 0, cast(str, object()), size_mm=20)

    with pytest.raises(TypeError, match=r"qr\(\) ecc must be one of"):
        qr("code", 0, 0, "hello", size_mm=20, ecc="Z")

    with pytest.raises(TypeError, match=r"qr\(\) size_mm must be positive"):
        qr("code", 0, 0, "hello", size_mm=0)

    with pytest.raises(TypeError, match=r"qr\(\) padding_mm must leave positive space"):
        qr("code", 0, 0, "hello", size_mm=20, padding_mm=10)



def test_image_clip_helper_renders_inline_defs(tmp_path: Path) -> None:
    asset = tmp_path / "logo.png"
    asset.write_bytes(b"\x89PNG\r\n\x1a\n")
    document = render(
        page(
            page_id="cover",
            filename="cover.svg",
            page_number=1,
            elements=[
                image(
                    "hero",
                    "logo.png",
                    10,
                    10,
                    20,
                    20,
                    clip=ellipse("hero_clip_shape", 20, 20, 8, 8, fill="white"),
                )
            ],
        )
    )

    content = render_document(document, config_dir=tmp_path).pages[0].content

    assert '<defs>' in content
    assert 'id="hero_clip"' in content
    assert 'clip-path="url(#hero_clip)"' in content
    assert '<ellipse id="hero_clip_shape"' in content
    assert '<image id="hero"' in content



def test_gradient_and_shadow_helpers_render(tmp_path: Path) -> None:
    document = render(
        page(
            page_id="cover",
            filename="cover.svg",
            page_number=1,
            defs=[
                linear_gradient_stops(
                    "panel_gradient",
                    [("0%", tokens.INK), ("100%", tokens.ACCENT, 0.6)],
                    angle_deg=45,
                ),
                drop_shadow("shadow_filter", blur=4, dy=2, alpha=0.8),
            ],
            elements=[
                rect(
                    "panel",
                    0,
                    0,
                    20,
                    20,
                    fill="url(#panel_gradient)",
                    filter="url(#shadow_filter)",
                )
            ],
        )
    )

    content = render_document(document, config_dir=tmp_path).pages[0].content

    assert 'id="panel_gradient_stop_1"' in content
    assert 'id="panel_gradient_stop_2"' in content
    assert 'stop-opacity="0.6"' in content
    assert 'id="shadow_filter"' in content
    assert 'id="shadow_filter_blur"' in content
    assert 'id="shadow_filter_alpha_curve"' in content
    assert 'slope="0.8"' in content



def test_extended_tokens_suppress_palette_warnings() -> None:
    tokens.extend(project_orange="#abcdef")
    document = render(
        page(
            page_id="cover",
            filename="cover.svg",
            page_number=1,
            elements=[rect("panel", 0, 0, 10, 10, fill=tokens.project_orange)],
        )
    )

    with warnings.catch_warnings(record=True) as recorded:
        warnings.simplefilter("always")
        validate_document(document)

    assert not [warning for warning in recorded if warning.category is ValidationWarning]


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



def test_wrapped_text_wraps_plain_text_and_supports_style_helpers(tmp_path: Path) -> None:
    card = block("card", at=(20, 40))
    document = render(
        page(
            page_id="cover",
            filename="cover.svg",
            page_number=1,
            elements=[
                wrapped_text(
                    "copy",
                    10,
                    20,
                    "Alpha beta gamma delta epsilon zeta eta theta.",
                    width_mm=32,
                    size_pt=12,
                    fill=tokens.INK,
                ),
                tokens.STYLES.body.wrapped_text(
                    "copy_style",
                    10,
                    50,
                    "Styled wrapping text should also split into multiple lines.",
                    width_mm=35,
                    max_lines=2,
                ),
                card.wrapped_text(
                    "body",
                    0,
                    0,
                    "Scoped block wrapping should preserve block offsets.",
                    width_mm=26,
                    size_pt=10,
                    fill=tokens.INK_2,
                ),
            ],
        )
    )

    content = render_document(document, config_dir=tmp_path).pages[0].content

    assert 'id="copy_line_1"' in content
    assert 'id="copy_line_2"' in content
    assert 'id="copy_style_line_2"' in content
    assert 'id="card_body_line_1"' in content
    assert 'id="card_body_line_2"' in content
    assert "…</tspan>" in content
    assert re.search(r'<tspan id="card_body_line_1"[^>]* x="56\.69" y="113\.39"', content)



def test_measure_text_and_measure_wrapped_text_return_metrics() -> None:
    inline = measure_text(
        [
            "Hello ",
            span(None, "world", style=tokens.STYLES.kicker, fill=tokens.ACCENT),
        ],
        style=tokens.STYLES.body,
        size_pt=12,
    )
    wrapped = measure_wrapped_text(
        "Alpha beta gamma delta epsilon zeta",
        width_mm=20,
        max_lines=2,
        size_pt=12,
    )

    assert inline.width_mm > 0
    assert inline.height_mm > 0
    assert inline.line_count == 1
    assert wrapped.width_mm <= 20
    assert wrapped.line_count == 2
    assert wrapped.truncated is True



def test_wrapped_text_supports_structured_content_and_warns_on_truncate(tmp_path: Path) -> None:
    with warnings.catch_warnings(record=True) as recorded:
        warnings.simplefilter("always")
        document = render(
            page(
                page_id="cover",
                filename="cover.svg",
                page_number=1,
                elements=[
                    wrapped_text(
                        "copy",
                        10,
                        20,
                        [
                            "Alpha ",
                            span(None, "beta", style=tokens.STYLES.kicker, fill=tokens.ACCENT),
                            " gamma delta epsilon zeta eta",
                        ],
                        width_mm=20,
                        max_lines=1,
                        size_pt=12,
                    )
                ],
            )
        )

    content = render_document(document, config_dir=tmp_path).pages[0].content

    assert any(item.category is TextLayoutWarning for item in recorded)
    assert 'id="copy_line_1"' in content
    assert 'fill="#c8a24a"' in content
    assert "…</tspan>" in content



def test_render_document_supports_document_level_defs_and_detects_collisions(
    tmp_path: Path,
) -> None:
    shared_defs = [
        linear_gradient_stops(
            "shared_gradient",
            [("0%", tokens.INK), ("100%", tokens.ACCENT)],
        ),
        grain("shared_grain", alpha=0.03),
    ]
    document = render(
        page(
            rect(
                "panel_one",
                0,
                0,
                20,
                20,
                fill="url(#shared_gradient)",
                filter="url(#shared_grain)",
            ),
            page_id="one",
            filename="one.svg",
            page_number=1,
        ),
        page(
            rect(
                "panel_two",
                0,
                0,
                20,
                20,
                fill="url(#shared_gradient)",
                filter="url(#shared_grain)",
            ),
            page_id="two",
            filename="two.svg",
            page_number=2,
        ),
        defs=shared_defs,
    )

    pages = render_document(document, config_dir=tmp_path).pages

    assert 'id="shared_gradient"' in pages[0].content
    assert 'id="shared_gradient"' in pages[1].content
    assert 'id="shared_grain"' in pages[0].content
    assert 'id="shared_grain"' in pages[1].content

    collision = render(
        page(
            page_id="cover",
            filename="cover.svg",
            page_number=1,
            defs=[
                linear_gradient(
                    "shared_gradient",
                    stop("page_stop", offset="0%", stop_color=tokens.LINE),
                )
            ],
            elements=[rect("panel", 0, 0, 10, 10, fill="url(#shared_gradient)")],
        ),
        defs=[
            linear_gradient(
                "shared_gradient",
                stop("doc_stop", offset="0%", stop_color=tokens.INK),
            )
        ],
    )

    with pytest.raises(RenderError, match=r"Duplicate element id: shared_gradient"):
        validate_document(collision)



def test_qr_padding_and_grain_helper_render(tmp_path: Path) -> None:
    document = render(
        page(
            page_id="cover",
            filename="cover.svg",
            page_number=1,
            defs=[grain("paper_grain", alpha=0.05)],
            elements=[
                rect("panel", 0, 0, 20, 20, fill=tokens.SOFT, filter="url(#paper_grain)"),
                qr(
                    "code",
                    10,
                    20,
                    "https://example.com",
                    size_mm=30,
                    border_modules=0,
                    padding_mm=2,
                    padding_fill=tokens.SOFT,
                    background_fill=tokens.WHITE,
                ),
            ],
        )
    )

    content = render_document(document, config_dir=tmp_path).pages[0].content

    assert 'id="paper_grain"' in content
    assert 'feTurbulence' in content
    assert '<rect id="code_pad"' in content
    assert '<rect id="code_bg"' in content
    assert '<path id="code_fg" d="M' in content
    assert re.search(r'<rect id="code_bg"[^>]* x="34\.02" y="62\.36"', content)



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
                    gaussian_blur("shadow_blur", in_="SourceAlpha", stdDeviation="4"),
                    offset("shadow_offset", dy="2"),
                    component_transfer(
                        "shadow_alpha",
                        func_a("shadow_alpha_curve", type="linear", slope="0.8"),
                    ),
                    merge(
                        "shadow_merge",
                        merge_node("shadow_merge_shadow"),
                        merge_node("shadow_merge_graphic", in_="SourceGraphic"),
                    ),
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


def test_path_builder_arc_to_emits_valid_svg_arc_flags() -> None:
    """arc_to must not scale the rotation or the arc flags.

    Regression: ``PathBuilder._push`` previously ran every value through
    the mm→pt scalar, turning ``sweep=True`` into ``2.83`` and breaking
    the resulting SVG arc (all major browsers reject non-0/1 arc flags).
    """
    from folio.dsl import path_builder

    arc = path_builder().move_to(0, 10).arc_to(10, 10, 0, 10, 0, sweep=True)
    # Command string: "M<...> A<rx> <ry> <rotation> <large> <sweep> <x> <y>"
    commands = arc.build().split()
    # M0 0 A<rx> <ry> <rotation> <large> <sweep> <x> <y>
    # Token index 4 = rotation (degrees, must be "0"),
    # index 5 = large-arc flag, index 6 = sweep flag.
    assert commands[4] == "0"  # rotation, not "0.0" and definitely not scaled
    assert commands[5] in {"0", "1"}
    assert commands[6] in {"0", "1"}
    assert commands[6] == "1"  # sweep=True → "1", not "2.83"

    not_swept = path_builder().move_to(0, 0).arc_to(5, 5, 0, 5, 5, sweep=False)
    assert not_swept.build().split()[6] == "0"


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
