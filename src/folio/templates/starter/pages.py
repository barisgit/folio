from __future__ import annotations

from content import (
    BRAND_NAME,
    BRAND_TAGLINE,
    CARDS,
    CTA_URL,
    DOCUMENT_KICKER,
    DOCUMENT_SUBTITLE,
    DOCUMENT_TITLE,
    FEATURES,
    HERO_LINE_1,
    HERO_LINE_2_ACCENT,
    HERO_LINE_2_PREFIX,
    HERO_LINE_3,
    METRICS,
    SPARKLINE_AXIS_LABELS,
    SPARKLINE_PEAK_INDEX,
    SPARKLINE_PEAK_LABEL,
    SPARKLINE_VALUES,
    TIMELINE,
)
from layout import (
    chart_axis_labels,
    content_card,
    corner_ticks,
    metric_tile,
    numbered_feature,
    rounded_photo,
    sparkline_chart,
)
from theme import (
    CHART_ANNOTATION,
    COUNTER_MONO_LIGHT,
    DISPLAY_SERIF,
    DISPLAY_XL,
    EYEBROW,
    EYEBROW_MUTED,
    GIANT_NUMBER,
    LEDE,
    PAGE_HEIGHT_MM,
    PAGE_WIDTH_MM,
    T,
)

from folio.dsl import (
    circle,
    drop_shadow,
    ellipse,
    group,
    linear_gradient_stops,
    page,
    polygon,
    qr,
    radial_gradient,
    rect,
    rule,
    stop,
    text,
    tokens,
    transform_builder,
    tspan,
    wrapped_text,
)
from folio.layout import cols, grid

PAGE_W = PAGE_WIDTH_MM
PAGE_H = PAGE_HEIGHT_MM
MARGIN_X = 14.0
TOTAL_PAGES = 3


def _counter_label(index: int) -> str:
    return f"{index:02d}  /  {TOTAL_PAGES:02d}"


def _shared_shadow_defs():
    return (
        drop_shadow("hero_shadow", blur=22, dx=0, dy=16, alpha=0.55),
        drop_shadow("card_shadow", blur=5, dx=0, dy=3, alpha=0.14),
        drop_shadow("tile_shadow", blur=4, dx=0, dy=2, alpha=0.12),
    )


def _cover_defs():
    return (
        linear_gradient_stops(
            "bg_cover_gradient",
            [
                ("0%", tokens.deep_navy),
                ("40%", tokens.INK),
                ("100%", tokens.ink_black),
            ],
            angle_deg=160,
        ),
        radial_gradient(
            "bg_glow_amber",
            stop("bg_glow_amber_1", offset="0%", stop_color=tokens.ACCENT, stop_opacity="0.55"),
            stop("bg_glow_amber_2", offset="70%", stop_color=tokens.ACCENT, stop_opacity="0"),
            cx="0.5",
            cy="0.5",
            r="0.5",
        ),
        radial_gradient(
            "bg_glow_blue",
            stop("bg_glow_blue_1", offset="0%", stop_color=tokens.BLUE_GLOW, stop_opacity="0.6"),
            stop("bg_glow_blue_2", offset="70%", stop_color=tokens.BLUE_GLOW, stop_opacity="0"),
            cx="0.5",
            cy="0.5",
            r="0.5",
        ),
        *_shared_shadow_defs(),
    )


def _cover_background():
    rotation = (
        transform_builder()
        .translate(PAGE_W * 0.55, PAGE_H * 0.58)
        .rotate(-8)
        .build()
    )
    return group(
        "background",
        "Background",
        rect("bg", 0, 0, PAGE_W, PAGE_H, fill="url(#bg_cover_gradient)"),
        ellipse("bg_glow_top", PAGE_W * 1.05, -18, PAGE_W * 0.7, PAGE_H * 0.42, fill="url(#bg_glow_amber)"),
        ellipse("bg_glow_bottom", -10, PAGE_H + 12, PAGE_W * 0.6, PAGE_H * 0.38, fill="url(#bg_glow_blue)"),
        group(
            "giant_number",
            "Giant Number",
            text(
                "giant_01",
                0,
                0,
                "01",
                style=GIANT_NUMBER,
                anchor="middle",
            ),
            transform=rotation,
        ),
        polygon(
            "diagonal_slash",
            [
                (-6.0, PAGE_H * 0.58),
                (PAGE_W * 0.42, PAGE_H * 0.50),
                (PAGE_W * 0.42, PAGE_H * 0.515),
                (-6.0, PAGE_H * 0.595),
            ],
            fill=tokens.WHITE,
            fill_opacity=0.05,
        ),
    )


def _cover_top_bar():
    return group(
        "top_bar",
        "Top Bar",
        circle("brand_disc", MARGIN_X + 4.0, 16.0, 4.2, fill=tokens.ACCENT),
        circle("brand_disc_inner", MARGIN_X + 4.0, 16.0, 1.7, fill=tokens.deep_navy),
        text(
            "brand_name",
            MARGIN_X + 11.5,
            15.4,
            BRAND_NAME,
            style=T.brand_name,
            size_pt=10.5,
            letter_spacing=1.8,
        ),
        text(
            "brand_tagline",
            MARGIN_X + 11.5,
            19.8,
            BRAND_TAGLINE,
            style=T.brand_tagline,
            size_pt=6.8,
            letter_spacing=2.6,
        ),
        text(
            "top_counter",
            PAGE_W - MARGIN_X,
            17.0,
            _counter_label(1),
            style=COUNTER_MONO_LIGHT,
            fill=tokens.ACCENT,
            anchor="end",
        ),
        rule(
            "sep_top",
            MARGIN_X,
            24.0,
            PAGE_W - 2 * MARGIN_X,
            fill=tokens.WHITE,
            opacity=0.12,
        ),
    )


def _cover_hero_text():
    return group(
        "hero_text",
        "Hero Text",
        text(
            "hero_eyebrow",
            MARGIN_X,
            36.0,
            DOCUMENT_KICKER,
            style=EYEBROW,
        ),
        text("hero_line_1", MARGIN_X, 60.0, HERO_LINE_1, style=DISPLAY_XL),
        text(
            "hero_line_2",
            MARGIN_X,
            80.0,
            (
                HERO_LINE_2_PREFIX + "  ",
                tspan("hero_line_2_accent", HERO_LINE_2_ACCENT, style=DISPLAY_SERIF),
                ".",
            ),
            style=DISPLAY_XL,
        ),
        text("hero_line_3", MARGIN_X, 100.0, HERO_LINE_3, style=DISPLAY_XL),
        wrapped_text(
            "hero_lede",
            MARGIN_X,
            116.0,
            DOCUMENT_SUBTITLE,
            width_mm=70.0,
            line_step_mm=4.8,
            max_lines=5,
            style=LEDE,
            size_pt=10,
        ),
    )


def _cover_hero_photo():
    photo_w = 78.0
    photo_h = 92.0
    photo_x = PAGE_W - MARGIN_X - photo_w
    photo_y = 52.0
    return rounded_photo(
        "hero_photo",
        photo_x,
        photo_y,
        photo_w,
        photo_h,
        "assets/hero_architecture.jpg",
        radius_mm=3.5,
        halo_offset_mm=3.2,
        halo_color=tokens.ACCENT,
        halo_opacity=0.4,
    )


def _cover_photo_caption():
    caption_x = PAGE_W - MARGIN_X - 78.0
    caption_y = 152.0
    return group(
        "hero_caption",
        "Hero Caption",
        rect(
            "caption_chip",
            caption_x,
            caption_y,
            78.0,
            10.0,
            fill=tokens.WHITE,
            fill_opacity=0.08,
            rx_mm=1.2,
            ry_mm=1.2,
        ),
        text(
            "caption_tag",
            caption_x + 4.0,
            caption_y + 4.0,
            "COVER STUDY",
            style=EYEBROW_MUTED,
            size_pt=6.4,
            letter_spacing=2.8,
        ),
        text(
            "caption_body",
            caption_x + 4.0,
            caption_y + 7.8,
            "Milwaukee Art Museum  ·  Santiago Calatrava",
            size_pt=7.0,
            fill=tokens.WHITE,
            fill_opacity=0.78,
            weight=400,
            letter_spacing=0.4,
        ),
    )


def _cover_features():
    layout = cols(3, inside=(MARGIN_X, PAGE_W - MARGIN_X), gap=6.0)
    features_y_top = 178.0
    return group(
        "features",
        "Features",
        rule(
            "sep_features_top",
            MARGIN_X,
            features_y_top - 8.0,
            PAGE_W - 2 * MARGIN_X,
            fill=tokens.WHITE,
            opacity=0.18,
        ),
        *[
            numbered_feature(
                index,
                layout.x(index),
                features_y_top,
                layout.column_width_mm,
                index_label,
                tag,
                body_text,
            )
            for index, (index_label, tag, body_text) in enumerate(
                [(idx, tag, " ".join(lines)) for (idx, tag, lines) in FEATURES],
                start=1,
            )
        ],
    )


def _cover_footer():
    qr_size = 20.0
    qr_x = MARGIN_X
    qr_y = 216.0
    return group(
        "footer",
        "Footer",
        rect(
            "qr_frame",
            qr_x - 1.5,
            qr_y - 1.5,
            qr_size + 3.0,
            qr_size + 3.0,
            fill=tokens.WHITE,
            fill_opacity=0.96,
            rx_mm=1.4,
            ry_mm=1.4,
        ),
        qr(
            "qr_cover",
            qr_x,
            qr_y,
            CTA_URL,
            size_mm=qr_size,
            ecc="M",
            border_modules=0,
            fill=tokens.deep_navy,
        ),
        text(
            "qr_label_eyebrow",
            qr_x + qr_size + 5.0,
            qr_y + 4.8,
            "SCAN TO READ",
            style=EYEBROW,
            size_pt=7.2,
            letter_spacing=3.0,
        ),
        text(
            "qr_label",
            qr_x + qr_size + 5.0,
            qr_y + 11.2,
            CTA_URL.replace("https://", ""),
            size_pt=8.4,
            fill=tokens.WHITE,
            fill_opacity=0.92,
            weight=700,
        ),
        text(
            "qr_hint",
            qr_x + qr_size + 5.0,
            qr_y + 16.8,
            "Release notes, live preview, sample specs.",
            size_pt=6.8,
            fill=tokens.MUTED_LIGHT,
            weight=400,
        ),
        rule(
            "sep_footer",
            MARGIN_X,
            PAGE_H - 13.5,
            PAGE_W - 2 * MARGIN_X,
            fill=tokens.WHITE,
            opacity=0.2,
        ),
        text(
            "footer_left",
            MARGIN_X,
            PAGE_H - 7.5,
            (
                tspan(
                    "footer_left_brand",
                    BRAND_NAME,
                    font_weight=800,
                    fill=tokens.ACCENT,
                    letter_spacing=1.6,
                ),
                "    DESIGNED IN PYTHON",
            ),
            style=T.meta,
            letter_spacing=1.2,
        ),
        text(
            "footer_right",
            PAGE_W - MARGIN_X,
            PAGE_H - 7.5,
            _counter_label(1),
            style=COUNTER_MONO_LIGHT,
            fill=tokens.MUTED_LIGHT,
            anchor="end",
        ),
    )


def build_cover():
    return page(
        page_id="cover",
        label="Cover",
        filename="01_cover.svg",
        page_number=1,
        width_mm=PAGE_W,
        height_mm=PAGE_H,
        defs=_cover_defs(),
        elements=[
            _cover_background(),
            corner_ticks("cover_crop", MARGIN_X - 4.0, 28.0, PAGE_W - 2 * (MARGIN_X - 4.0), PAGE_H - 42.0, color=tokens.WHITE, tick_mm=2.6),
            _cover_hero_photo(),
            _cover_photo_caption(),
            _cover_top_bar(),
            _cover_hero_text(),
            _cover_features(),
            _cover_footer(),
        ],
    )


def _features_defs():
    return (
        linear_gradient_stops(
            "features_bg_gradient",
            [("0%", tokens.WHITE), ("100%", tokens.mist)],
            angle_deg=180,
        ),
        linear_gradient_stops(
            "cta_gradient",
            [("0%", tokens.deep_navy), ("100%", tokens.mid_navy)],
            angle_deg=135,
        ),
        *_shared_shadow_defs(),
    )


def _features_header():
    return group(
        "header",
        "Header",
        text(
            "masthead_kicker",
            MARGIN_X,
            18.0,
            "FOLIO STARTER KIT",
            style=T.section_label,
        ),
        text(
            "masthead_counter",
            PAGE_W - MARGIN_X,
            18.0,
            _counter_label(2),
            style=T.counter_mono,
            anchor="end",
        ),
        rule(
            "sep_top",
            MARGIN_X,
            22.0,
            PAGE_W - 2 * MARGIN_X,
            fill=tokens.INK,
            opacity=0.12,
        ),
        text(
            "page_title",
            MARGIN_X,
            46.0,
            (
                "A tour of the ",
                tspan(
                    "page_title_em",
                    "typed DSL",
                    font_weight=700,
                    fill=tokens.ACCENT_DARK,
                    font_style="italic",
                    font_family="'Playfair Display', 'Iowan Old Style', Georgia, serif",
                ),
                ".",
            ),
            size_pt=30,
            weight=300,
            fill=tokens.INK,
            letter_spacing=-1.0,
        ),
        wrapped_text(
            "page_lede",
            MARGIN_X,
            56.0,
            "Typed primitives, shared tokens, and layout helpers compose into production-grade pages — reconcile-safe and diff-ready from the very first build.",
            width_mm=PAGE_W - 2 * MARGIN_X - 8.0,
            style=T.body_large,
            line_step_mm=5.2,
            max_lines=3,
        ),
    )


def _features_cards():
    cards_grid = grid(
        2,
        2,
        inside=(MARGIN_X, 82.0, PAGE_W - 2 * MARGIN_X, 96.0),
        col_gap=6.0,
        row_gap=6.0,
    )
    return group(
        "cards",
        "Cards",
        *[
            content_card(
                index,
                x_mm,
                y_mm,
                cards_grid.cell_width_mm,
                cards_grid.cell_height_mm,
                icon_ref,
                tag,
                title,
                " ".join(body_lines),
            )
            for index, (icon_ref, tag, title, body_lines) in enumerate(CARDS, start=1)
            for x_mm, y_mm in [cards_grid.cell_origin(index)]
        ],
    )


def _features_cta():
    panel_x = MARGIN_X
    panel_y = 192.0
    panel_w = PAGE_W - 2 * MARGIN_X
    panel_h = 58.0
    qr_size = 22.0
    qr_x = panel_x + panel_w - qr_size - 10.0
    qr_y = panel_y + (panel_h - qr_size) / 2
    return group(
        "cta",
        "CTA",
        rect(
            "cta_panel",
            panel_x,
            panel_y,
            panel_w,
            panel_h,
            fill="url(#cta_gradient)",
            rx_mm=3.0,
            ry_mm=3.0,
        ),
        polygon(
            "cta_wedge",
            [
                (panel_x, panel_y),
                (panel_x + 40.0, panel_y),
                (panel_x + 10.0, panel_y + 14.0),
                (panel_x, panel_y + 14.0),
            ],
            fill=tokens.ACCENT,
            fill_opacity=0.2,
        ),
        polygon(
            "cta_stripe",
            [
                (panel_x, panel_y),
                (panel_x + 14.0, panel_y),
                (panel_x, panel_y + 14.0),
            ],
            fill=tokens.ACCENT,
        ),
        text(
            "cta_eyebrow",
            panel_x + 10.0,
            panel_y + 12.0,
            "NEXT STEPS",
            style=T.audience_title,
            letter_spacing=2.8,
        ),
        *[
            group(
                f"cta_step_{index}",
                f"CTA Step {index}",
                ellipse(
                    f"cta_step_{index}_bullet",
                    panel_x + 12.0,
                    panel_y + 22.0 + (index - 1) * 11.0,
                    1.0,
                    1.0,
                    fill=tokens.ACCENT,
                ),
                text(
                    f"cta_step_{index}_title",
                    panel_x + 16.0,
                    panel_y + 23.2 + (index - 1) * 11.0,
                    title,
                    style=T.audience_body,
                    fill=tokens.WHITE,
                    weight=700,
                    letter_spacing=0.4,
                ),
                text(
                    f"cta_step_{index}_body",
                    panel_x + 16.0,
                    panel_y + 28.0 + (index - 1) * 11.0,
                    body,
                    style=T.audience_body,
                    fill=tokens.MUTED_LIGHT,
                    weight=400,
                    size_pt=7.4,
                ),
            )
            for index, (title, body) in enumerate(TIMELINE, start=1)
        ],
        rect(
            "cta_qr_frame",
            qr_x - 1.2,
            qr_y - 1.2,
            qr_size + 2.4,
            qr_size + 2.4,
            fill=tokens.WHITE,
            rx_mm=1.0,
            ry_mm=1.0,
        ),
        qr(
            "cta_qr",
            qr_x,
            qr_y,
            CTA_URL,
            size_mm=qr_size,
            ecc="M",
            border_modules=0,
            fill=tokens.deep_navy,
        ),
        text(
            "cta_qr_label",
            qr_x + qr_size / 2,
            qr_y + qr_size + 4.2,
            "SCAN",
            size_pt=6.4,
            weight=800,
            fill=tokens.ACCENT,
            anchor="middle",
            letter_spacing=2.6,
        ),
    )


def _shared_footer(page_number: int):
    return group(
        "footer",
        "Footer",
        rule(
            "sep_footer",
            MARGIN_X,
            PAGE_H - 13.5,
            PAGE_W - 2 * MARGIN_X,
            fill=tokens.LINE,
        ),
        text(
            "footer_left",
            MARGIN_X,
            PAGE_H - 7.5,
            (
                tspan(
                    "footer_left_brand",
                    BRAND_NAME,
                    font_weight=800,
                    fill=tokens.INK,
                    letter_spacing=1.6,
                ),
                "    " + BRAND_TAGLINE,
            ),
            style=T.meta,
            fill=tokens.MUTED,
            letter_spacing=1.0,
        ),
        text(
            "footer_right",
            PAGE_W - MARGIN_X,
            PAGE_H - 7.5,
            _counter_label(page_number),
            style=T.counter_mono,
            fill=tokens.MUTED,
            anchor="end",
        ),
    )


def build_features():
    return page(
        page_id="features",
        label="Features",
        filename="02_features.svg",
        page_number=2,
        width_mm=PAGE_W,
        height_mm=PAGE_H,
        defs=_features_defs(),
        elements=[
            rect("bg", 0, 0, PAGE_W, PAGE_H, fill="url(#features_bg_gradient)"),
            _features_header(),
            _features_cards(),
            _features_cta(),
            _shared_footer(2),
        ],
    )


def _metrics_defs():
    return (
        linear_gradient_stops(
            "metrics_bg_gradient",
            [("0%", tokens.WHITE), ("100%", tokens.mist)],
            angle_deg=180,
        ),
        linear_gradient_stops(
            "chart_area_gradient",
            [("0%", tokens.ACCENT, 0.32), ("100%", tokens.ACCENT, 0.0)],
            angle_deg=180,
        ),
        *_shared_shadow_defs(),
    )


def _metrics_header():
    return group(
        "header",
        "Header",
        text(
            "masthead_kicker",
            MARGIN_X,
            18.0,
            "METRICS  /  TTM",
            style=T.section_label,
        ),
        text(
            "masthead_counter",
            PAGE_W - MARGIN_X,
            18.0,
            _counter_label(3),
            style=T.counter_mono,
            anchor="end",
        ),
        rule(
            "sep_top",
            MARGIN_X,
            22.0,
            PAGE_W - 2 * MARGIN_X,
            fill=tokens.INK,
            opacity=0.12,
        ),
        text(
            "page_title",
            MARGIN_X,
            46.0,
            (
                "Operating ",
                tspan(
                    "page_title_em",
                    "metrics",
                    font_weight=700,
                    fill=tokens.ACCENT_DARK,
                    font_style="italic",
                    font_family="'Playfair Display', 'Iowan Old Style', Georgia, serif",
                ),
                ".",
            ),
            size_pt=30,
            weight=300,
            fill=tokens.INK,
            letter_spacing=-1.0,
        ),
    )


def _metrics_tiles():
    tiles_grid = grid(
        3,
        1,
        inside=(MARGIN_X, 58.0, PAGE_W - 2 * MARGIN_X, 44.0),
        col_gap=4.0,
    )
    return group(
        "metric_tiles",
        "Metric Tiles",
        *[
            metric_tile(
                index,
                x_mm,
                y_mm,
                tiles_grid.cell_width_mm,
                tiles_grid.cell_height_mm,
                label,
                value,
                delta,
            )
            for index, (label, value, delta) in enumerate(METRICS, start=1)
            for x_mm, y_mm in [tiles_grid.cell_origin(index)]
        ],
    )


def _metrics_chart():
    chart_frame_x = MARGIN_X
    chart_frame_y = 114.0
    chart_frame_w = PAGE_W - 2 * MARGIN_X
    chart_frame_h = 86.0
    inner_pad = 6.0
    chart_x = chart_frame_x + inner_pad
    chart_y = chart_frame_y + 24.0
    chart_w = chart_frame_w - 2 * inner_pad
    chart_h = 44.0
    return group(
        "chart",
        "Chart",
        rect(
            "chart_frame",
            chart_frame_x,
            chart_frame_y,
            chart_frame_w,
            chart_frame_h,
            fill=tokens.WHITE,
            stroke=tokens.LINE,
            stroke_width=0.3,
            rx_mm=2.6,
            ry_mm=2.6,
            filter="url(#tile_shadow)",
        ),
        rect(
            "chart_frame_accent",
            chart_frame_x,
            chart_frame_y,
            chart_frame_w,
            1.2,
            fill=tokens.ACCENT,
            rx_mm=2.6,
            ry_mm=2.6,
        ),
        text(
            "chart_label",
            chart_frame_x + inner_pad,
            chart_frame_y + 12.0,
            "PAGES PUBLISHED PER MONTH",
            style=T.section_label,
            letter_spacing=2.4,
        ),
        text(
            "chart_value",
            chart_frame_x + chart_frame_w - inner_pad,
            chart_frame_y + 12.0,
            (
                tspan(
                    "chart_value_big",
                    "+31%",
                    font_weight=800,
                    fill=tokens.INK,
                    letter_spacing=-0.3,
                    font_size_pt=14,
                ),
                "   vs. prior period",
            ),
            style=T.meta,
            fill=tokens.MUTED,
            anchor="end",
        ),
        sparkline_chart(
            "main_sparkline",
            chart_x,
            chart_y,
            chart_w,
            chart_h,
            SPARKLINE_VALUES,
            peak_index=SPARKLINE_PEAK_INDEX,
            peak_label=SPARKLINE_PEAK_LABEL,
        ),
        *chart_axis_labels(
            "main_sparkline_axis",
            SPARKLINE_AXIS_LABELS,
            chart_x,
            chart_y + chart_h + 5.0,
            chart_w,
        ),
    )


def _metrics_legend():
    panel_x = MARGIN_X
    panel_y = 210.0
    panel_w = PAGE_W - 2 * MARGIN_X
    panel_h = 44.0
    return group(
        "legend",
        "Legend",
        rect(
            "legend_panel",
            panel_x,
            panel_y,
            panel_w,
            panel_h,
            fill=tokens.INK,
            rx_mm=2.6,
            ry_mm=2.6,
        ),
        polygon(
            "legend_slash",
            [
                (panel_x + panel_w - 42.0, panel_y),
                (panel_x + panel_w, panel_y),
                (panel_x + panel_w, panel_y + 18.0),
            ],
            fill=tokens.ACCENT,
            fill_opacity=0.22,
        ),
        polygon(
            "legend_stripe",
            [
                (panel_x + panel_w - 14.0, panel_y),
                (panel_x + panel_w, panel_y),
                (panel_x + panel_w, panel_y + 14.0),
            ],
            fill=tokens.ACCENT,
        ),
        text(
            "legend_eyebrow",
            panel_x + 10.0,
            panel_y + 12.0,
            "PRIMITIVES ON THIS PAGE",
            style=T.audience_title,
        ),
        wrapped_text(
            "legend_body",
            panel_x + 10.0,
            panel_y + 22.0,
            "polyline() — the sparkline and gridlines.  polygon() — the corner wedges and stripes.  path_builder() — the filled area under the curve.  drop_shadow() — soft elevation on every card and tile.",
            width_mm=panel_w - 20.0,
            line_step_mm=4.4,
            max_lines=4,
            style=T.audience_body,
            fill=tokens.TEXT_SOFT,
            size_pt=8,
        ),
    )


def build_metrics():
    return page(
        page_id="metrics",
        label="Metrics",
        filename="03_metrics.svg",
        page_number=3,
        width_mm=PAGE_W,
        height_mm=PAGE_H,
        defs=_metrics_defs(),
        elements=[
            rect("bg", 0, 0, PAGE_W, PAGE_H, fill="url(#metrics_bg_gradient)"),
            _metrics_header(),
            _metrics_tiles(),
            _metrics_chart(),
            _metrics_legend(),
            _shared_footer(3),
        ],
    )


__all__ = ["build_cover", "build_features", "build_metrics"]
