from __future__ import annotations

from content import (
    BRAND_NAME,
    BRAND_TAGLINE,
    CARDS,
    CTA_URL,
    DOCUMENT_KICKER,
    DOCUMENT_TITLE,
    FEATURES,
    FEATURES_PAGE_LEDE_PARTS,
    HERO_LEDE_PARTS,
    HERO_WORDS,
    METRICS,
    METRICS_LEDE_PARTS,
    METRICS_LEGEND_PARTS,
    PHOTO_CAPTION_BODY,
    PHOTO_CAPTION_TAG,
    SPARKLINE_AXIS_LABELS,
    SPARKLINE_PEAK_INDEX,
    SPARKLINE_PEAK_LABEL,
    SPARKLINE_VALUES,
    TIMELINE,
)
from layout import (
    brand_chip,
    build_rich_content,
    content_card,
    corner_ticks,
    counter_pill,
    metric_tile,
    numbered_feature,
    rounded_photo,
)
from theme import (
    CAPTION_LIGHT,
    COUNTER_MONO_LIGHT,
    DISPLAY_L,
    DISPLAY_L_SERIF,
    DISPLAY_SERIF,
    DISPLAY_XL,
    EYEBROW,
    EYEBROW_DARK,
    EYEBROW_MUTED,
    GIANT_NUMBER,
    LEDE_DARK,
    LEDE_DARK_EM,
    LEDE_LIGHT,
    LEDE_LIGHT_EM,
    MARGIN_X_MM,
    PAGE_SIZE_MM,
    T,
    TOTAL_PAGES,
)

from folio.dsl import (
    block,
    chart,
    ellipse,
    grain,
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
    tspan,
    wrapped_text,
)
from folio.layout import cols, grid

PAGE_W = PAGE_SIZE_MM
PAGE_H = PAGE_SIZE_MM
MARGIN_X = MARGIN_X_MM


def _counter_label(index: int) -> str:
    return f"{index:02d}  /  {TOTAL_PAGES:02d}"


def _bg_noise_overlay(element_id: str, filter_url: str):
    return rect(
        element_id,
        0,
        0,
        PAGE_W,
        PAGE_H,
        fill=tokens.WHITE,
        fill_opacity=0,
        filter=filter_url,
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
            angle_deg=155,
        ),
        radial_gradient(
            "bg_glow_amber",
            stop("bg_glow_amber_1", offset="0%", stop_color=tokens.ACCENT, stop_opacity="0.6"),
            stop("bg_glow_amber_2", offset="70%", stop_color=tokens.ACCENT, stop_opacity="0"),
            cx="0.5",
            cy="0.5",
            r="0.5",
        ),
        radial_gradient(
            "bg_glow_blue",
            stop("bg_glow_blue_1", offset="0%", stop_color=tokens.BLUE_GLOW, stop_opacity="0.55"),
            stop("bg_glow_blue_2", offset="70%", stop_color=tokens.BLUE_GLOW, stop_opacity="0"),
            cx="0.5",
            cy="0.5",
            r="0.5",
        ),
        grain("cover_grain", base_frequency=0.85, num_octaves=2, alpha=0.08, seed=17),
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
        linear_gradient_stops(
            "legend_gradient",
            [("0%", tokens.INK), ("100%", tokens.mid_navy)],
            angle_deg=135,
        ),
    )


def _cover_background():
    giant_block = block("cover_giant", at=(PAGE_W * 0.22, PAGE_H * 0.55))
    rotation_transform = giant_block.transform_builder().rotate(-8).build()
    return group(
        "background",
        "Background",
        rect("bg", 0, 0, PAGE_W, PAGE_H, fill="url(#bg_cover_gradient)"),
        ellipse(
            "bg_glow_top",
            PAGE_W * 1.05,
            -PAGE_H * 0.08,
            PAGE_W * 0.75,
            PAGE_H * 0.55,
            fill="url(#bg_glow_amber)",
        ),
        ellipse(
            "bg_glow_bottom",
            -PAGE_W * 0.05,
            PAGE_H + 10,
            PAGE_W * 0.6,
            PAGE_H * 0.42,
            fill="url(#bg_glow_blue)",
        ),
        group(
            "cover_giant_group",
            "Giant Number",
            text(
                "cover_giant_01",
                0,
                0,
                "01",
                style=GIANT_NUMBER,
                anchor="middle",
            ),
            transform=rotation_transform,
        ),
        polygon(
            "bg_diagonal_slash",
            [
                (-6.0, PAGE_H * 0.62),
                (PAGE_W * 0.45, PAGE_H * 0.52),
                (PAGE_W * 0.45, PAGE_H * 0.535),
                (-6.0, PAGE_H * 0.635),
            ],
            fill=tokens.WHITE,
            fill_opacity=0.04,
        ),
        _bg_noise_overlay("cover_grain_overlay", "url(#cover_grain)"),
    )


def _cover_top_bar():
    chip, chip_w, chip_h = brand_chip(
        "cover_brand_chip",
        MARGIN_X,
        12.0,
        BRAND_NAME,
        BRAND_TAGLINE,
        light=True,
    )
    return group(
        "top_bar",
        "Top Bar",
        chip,
        counter_pill(
            "cover_counter",
            PAGE_W - MARGIN_X,
            12.0 + (chip_h - 8.0) / 2,
            _counter_label(1),
            light=True,
        ),
        rule(
            "sep_top",
            MARGIN_X,
            12.0 + chip_h + 6.0,
            PAGE_W - 2 * MARGIN_X,
            fill=tokens.WHITE,
            opacity=0.12,
        ),
    )


def _cover_hero_text():
    eyebrow_metrics = None
    hero_parts: list = []
    for index, (kind, word) in enumerate(HERO_WORDS, start=1):
        if kind == "emphasis":
            hero_parts.append(tspan(f"hero_word_em_{index}", word, style=DISPLAY_SERIF))
        elif kind == "divider":
            hero_parts.append(word)
        else:
            hero_parts.append(word + " ")

    lede_rich, _ = build_rich_content(
        HERO_LEDE_PARTS,
        LEDE_LIGHT,
        LEDE_LIGHT_EM,
        prefix_id="hero_lede",
    )

    return group(
        "hero_text",
        "Hero Text",
        text(
            "hero_eyebrow",
            MARGIN_X,
            58.0,
            DOCUMENT_KICKER,
            style=EYEBROW,
        ),
        text("hero_line_1", MARGIN_X, 90.0, "Design.", style=DISPLAY_XL),
        text(
            "hero_line_2",
            MARGIN_X,
            112.0,
            (
                "Render  ",
                tspan("hero_line_2_em", "anywhere", style=DISPLAY_SERIF),
                ".",
            ),
            style=DISPLAY_XL,
        ),
        text("hero_line_3", MARGIN_X, 134.0, "Repeat.", style=DISPLAY_XL),
        wrapped_text(
            "hero_lede",
            MARGIN_X,
            160.0,
            lede_rich,
            width_mm=PAGE_W * 0.46,
            line_step_mm=5.2,
            max_lines=5,
            style=LEDE_LIGHT,
        ),
    )


def _cover_hero_photo():
    photo_w = PAGE_W * 0.44
    photo_h = PAGE_H * 0.56
    photo_x = PAGE_W - MARGIN_X - photo_w
    photo_y = 58.0
    return group(
        "hero_photo_group",
        "Hero Photo Group",
        rounded_photo(
            "hero_photo",
            photo_x,
            photo_y,
            photo_w,
            photo_h,
            "assets/hero_typography.jpg",
            radius_mm=3.5,
            halo_offset_mm=3.6,
            halo_color=tokens.ACCENT,
            halo_opacity=0.4,
        ),
        rect(
            "hero_caption_frame",
            photo_x,
            photo_y + photo_h + 3.0,
            photo_w,
            14.0,
            fill=tokens.WHITE,
            fill_opacity=0.08,
            rx_mm=1.6,
            ry_mm=1.6,
        ),
        text(
            "hero_caption_tag",
            photo_x + 5.0,
            photo_y + photo_h + 8.0,
            PHOTO_CAPTION_TAG,
            style=EYEBROW_MUTED,
        ),
        text(
            "hero_caption_body",
            photo_x + 5.0,
            photo_y + photo_h + 12.8,
            PHOTO_CAPTION_BODY,
            style=CAPTION_LIGHT,
        ),
    )


def _cover_scan_cta():
    qr_size = 22.0
    qr_x = MARGIN_X
    qr_y = PAGE_H - 60.0
    return group(
        "scan_cta",
        "Scan CTA",
        qr(
            "qr_cover",
            qr_x,
            qr_y,
            CTA_URL,
            size_mm=qr_size,
            ecc="M",
            border_modules=0,
            fill=tokens.deep_navy,
            padding_mm=2.2,
            padding_fill=tokens.WHITE,
        ),
        text(
            "qr_label_eyebrow",
            qr_x + qr_size + 8.0,
            qr_y + 5.0,
            "SCAN TO READ",
            style=EYEBROW,
        ),
        text(
            "qr_label",
            qr_x + qr_size + 8.0,
            qr_y + 12.0,
            CTA_URL.replace("https://", ""),
            size_pt=10,
            fill=tokens.WHITE,
            fill_opacity=0.95,
            weight=700,
        ),
        text(
            "qr_hint",
            qr_x + qr_size + 8.0,
            qr_y + 17.4,
            "Release notes, live preview, sample specs.",
            size_pt=7.2,
            fill=tokens.MUTED_LIGHT,
            weight=400,
        ),
    )


def _cover_footer():
    return group(
        "footer",
        "Footer",
        rule(
            "sep_footer",
            MARGIN_X,
            PAGE_H - 18.0,
            PAGE_W - 2 * MARGIN_X,
            fill=tokens.WHITE,
            opacity=0.22,
        ),
        text(
            "footer_left",
            MARGIN_X,
            PAGE_H - 10.0,
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
            PAGE_H - 10.0,
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
            corner_ticks(
                "cover_crop",
                MARGIN_X - 6.0,
                MARGIN_X - 6.0,
                PAGE_W - 2 * (MARGIN_X - 6.0),
                PAGE_H - 2 * (MARGIN_X - 6.0),
                color=tokens.WHITE,
                tick_mm=2.8,
                opacity=0.28,
            ),
            _cover_hero_photo(),
            _cover_top_bar(),
            _cover_hero_text(),
            _cover_scan_cta(),
            _cover_footer(),
        ],
    )


def _features_header():
    chip, chip_w, chip_h = brand_chip(
        "features_brand_chip",
        MARGIN_X,
        12.0,
        BRAND_NAME,
        BRAND_TAGLINE,
        light=False,
    )
    lede_rich, _ = build_rich_content(
        FEATURES_PAGE_LEDE_PARTS,
        LEDE_DARK,
        LEDE_DARK_EM,
        prefix_id="features_lede",
    )
    return group(
        "header",
        "Header",
        chip,
        counter_pill(
            "features_counter",
            PAGE_W - MARGIN_X,
            12.0 + (chip_h - 8.0) / 2,
            _counter_label(2),
            light=False,
        ),
        rule(
            "sep_top",
            MARGIN_X,
            12.0 + chip_h + 6.0,
            PAGE_W - 2 * MARGIN_X,
            fill=tokens.INK,
            opacity=0.12,
        ),
        text(
            "page_title",
            MARGIN_X,
            58.0,
            (
                "A tour of the ",
                tspan("page_title_em", "typed DSL", style=DISPLAY_L_SERIF),
                ".",
            ),
            style=DISPLAY_L,
        ),
        wrapped_text(
            "page_lede",
            MARGIN_X,
            76.0,
            lede_rich,
            width_mm=PAGE_W - 2 * MARGIN_X - 10.0,
            line_step_mm=5.4,
            max_lines=3,
            style=LEDE_DARK,
        ),
    )


def _features_cards():
    cards_grid = grid(
        2,
        2,
        inside=(MARGIN_X, 104.0, PAGE_W - 2 * MARGIN_X, 94.0),
        col_gap=7.0,
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
                body_text,
            )
            for index, (icon_ref, tag, title, body_text) in enumerate(CARDS, start=1)
            for x_mm, y_mm in [cards_grid.cell_origin(index)]
        ],
    )


def _features_cta():
    panel_x = MARGIN_X
    panel_y = 204.0
    panel_w = PAGE_W - 2 * MARGIN_X
    panel_h = 16.0
    qr_size = 10.0
    qr_x = panel_x + panel_w - qr_size - 4.0
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
            rx_mm=2.4,
            ry_mm=2.4,
        ),
        polygon(
            "cta_stripe",
            [
                (panel_x, panel_y),
                (panel_x + 12.0, panel_y),
                (panel_x, panel_y + 12.0),
            ],
            fill=tokens.ACCENT,
        ),
        text(
            "cta_eyebrow",
            panel_x + 10.0,
            panel_y + 6.2,
            "NEXT STEPS",
            size_pt=7.6,
            weight=800,
            fill=tokens.ACCENT,
            letter_spacing=2.8,
        ),
        text(
            "cta_steps",
            panel_x + 10.0,
            panel_y + 12.6,
            (
                tspan(
                    "cta_step_1_num",
                    "01  ",
                    font_weight=800,
                    fill=tokens.ACCENT,
                    letter_spacing=1.0,
                    font_family=tokens.MONO_FONT_FAMILY,
                ),
                "Edit content.py  ",
                tspan(
                    "cta_step_2_num",
                    "02  ",
                    font_weight=800,
                    fill=tokens.ACCENT,
                    letter_spacing=1.0,
                    font_family=tokens.MONO_FONT_FAMILY,
                ),
                "Shape the theme  ",
                tspan(
                    "cta_step_3_num",
                    "03  ",
                    font_weight=800,
                    fill=tokens.ACCENT,
                    letter_spacing=1.0,
                    font_family=tokens.MONO_FONT_FAMILY,
                ),
                "folio build & preview",
            ),
            size_pt=7.4,
            weight=500,
            fill=tokens.TEXT_SOFT,
            letter_spacing=0.2,
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
            padding_mm=1.2,
            padding_fill=tokens.WHITE,
        ),
    )


def _shared_footer(page_number: int):
    return group(
        "footer",
        "Footer",
        rule(
            "sep_footer",
            MARGIN_X,
            PAGE_H - 18.0,
            PAGE_W - 2 * MARGIN_X,
            fill=tokens.LINE,
        ),
        text(
            "footer_left",
            MARGIN_X,
            PAGE_H - 10.0,
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
            PAGE_H - 10.0,
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
            _bg_noise_overlay("features_grain_overlay", "url(#paper_grain)"),
            _features_header(),
            _features_cards(),
            _features_cta(),
            _shared_footer(2),
        ],
    )


def _metrics_header():
    chip, chip_w, chip_h = brand_chip(
        "metrics_brand_chip",
        MARGIN_X,
        12.0,
        BRAND_NAME,
        BRAND_TAGLINE,
        light=False,
    )
    lede_rich, _ = build_rich_content(
        METRICS_LEDE_PARTS,
        LEDE_DARK,
        LEDE_DARK_EM,
        prefix_id="metrics_lede",
    )
    return group(
        "header",
        "Header",
        chip,
        counter_pill(
            "metrics_counter",
            PAGE_W - MARGIN_X,
            12.0 + (chip_h - 8.0) / 2,
            _counter_label(3),
            light=False,
        ),
        rule(
            "sep_top",
            MARGIN_X,
            12.0 + chip_h + 6.0,
            PAGE_W - 2 * MARGIN_X,
            fill=tokens.INK,
            opacity=0.12,
        ),
        text(
            "page_title",
            MARGIN_X,
            58.0,
            (
                "Operating ",
                tspan("page_title_em", "metrics", style=DISPLAY_L_SERIF),
                ".",
            ),
            style=DISPLAY_L,
        ),
        wrapped_text(
            "page_lede",
            MARGIN_X,
            74.0,
            lede_rich,
            width_mm=PAGE_W - 2 * MARGIN_X - 10.0,
            line_step_mm=5.2,
            max_lines=2,
            style=LEDE_DARK,
        ),
    )


def _metrics_tiles():
    tiles_grid = grid(
        3,
        1,
        inside=(MARGIN_X, 96.0, PAGE_W - 2 * MARGIN_X, 44.0),
        col_gap=6.0,
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
    frame_x = MARGIN_X
    frame_y = 148.0
    frame_w = PAGE_W - 2 * MARGIN_X
    frame_h = 54.0
    inner_pad = 7.0
    mpl_x = frame_x + inner_pad
    mpl_y = frame_y + 18.0
    mpl_w = frame_w - 2 * inner_pad
    mpl_h = frame_h - 24.0

    @chart(
        "main_chart",
        x_mm=mpl_x,
        y_mm=mpl_y,
        width_mm=mpl_w,
        height_mm=mpl_h,
        dpi=300,
    )
    def main_chart(ax) -> None:
        months = list(SPARKLINE_AXIS_LABELS)
        step = max(1, len(SPARKLINE_VALUES) // len(months))
        xs = list(range(len(SPARKLINE_VALUES)))
        ax.bar(xs, SPARKLINE_VALUES, color=tokens.ACCENT, alpha=0.28, width=0.72, zorder=1)
        ax.plot(xs, SPARKLINE_VALUES, color=tokens.ACCENT_DARK, linewidth=1.6, zorder=3)
        peak = SPARKLINE_PEAK_INDEX
        ax.scatter([peak], [SPARKLINE_VALUES[peak]], s=36, color=tokens.INK, zorder=4)
        ax.annotate(
            SPARKLINE_PEAK_LABEL,
            xy=(peak, SPARKLINE_VALUES[peak]),
            xytext=(-6, 8),
            textcoords="offset points",
            ha="right",
            fontsize=7,
            color=tokens.INK,
        )
        ax.set_xticks(xs[::step])
        ax.set_xticklabels(months, fontsize=6, color=tokens.MUTED)
        ax.tick_params(axis="x", length=0, pad=3)
        ax.set_yticks([])
        for spine in ("top", "right", "left"):
            ax.spines[spine].set_visible(False)
        ax.spines["bottom"].set_color(tokens.LINE)
        ax.spines["bottom"].set_linewidth(0.4)
        ax.margins(x=0.02)

    return group(
        "chart",
        "Chart",
        rect(
            "chart_frame",
            frame_x,
            frame_y,
            frame_w,
            frame_h,
            fill=tokens.WHITE,
            stroke=tokens.LINE,
            stroke_width=0.3,
            rx_mm=3.0,
            ry_mm=3.0,
            filter="url(#tile_shadow)",
        ),
        rect(
            "chart_frame_accent",
            frame_x,
            frame_y,
            frame_w,
            1.4,
            fill=tokens.ACCENT,
            rx_mm=3.0,
            ry_mm=3.0,
        ),
        text(
            "chart_label",
            frame_x + inner_pad,
            frame_y + 12.0,
            "PAGES PUBLISHED PER MONTH",
            style=T.section_label,
            letter_spacing=2.4,
        ),
        text(
            "chart_value",
            frame_x + frame_w - inner_pad,
            frame_y + 12.0,
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
        main_chart,
    )


def _metrics_legend():
    panel_x = MARGIN_X
    panel_y = 204.0
    panel_w = PAGE_W - 2 * MARGIN_X
    panel_h = 14.0
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
            rx_mm=2.0,
            ry_mm=2.0,
        ),
        polygon(
            "legend_stripe",
            [
                (panel_x, panel_y),
                (panel_x + 10.0, panel_y),
                (panel_x, panel_y + 10.0),
            ],
            fill=tokens.ACCENT,
        ),
        text(
            "legend_eyebrow",
            panel_x + 8.0,
            panel_y + 9.0,
            "PRIMITIVES",
            size_pt=7.0,
            weight=800,
            fill=tokens.ACCENT,
            letter_spacing=2.8,
        ),
        text(
            "legend_body",
            panel_x + 44.0,
            panel_y + 9.0,
            (
                tspan(
                    "legend_tspan_1",
                    "chart()",
                    font_family=tokens.MONO_FONT_FAMILY,
                    font_weight=700,
                    fill=tokens.WHITE,
                ),
                "  matplotlib   ",
                tspan(
                    "legend_tspan_2",
                    "polygon",
                    font_family=tokens.MONO_FONT_FAMILY,
                    font_weight=700,
                    fill=tokens.WHITE,
                ),
                "  wedges   ",
                tspan(
                    "legend_tspan_3",
                    "path_builder",
                    font_family=tokens.MONO_FONT_FAMILY,
                    font_weight=700,
                    fill=tokens.WHITE,
                ),
                "  callouts   ",
                tspan(
                    "legend_tspan_4",
                    "drop_shadow",
                    font_family=tokens.MONO_FONT_FAMILY,
                    font_weight=700,
                    fill=tokens.WHITE,
                ),
                "  elevation",
            ),
            size_pt=7.2,
            weight=400,
            fill=tokens.MUTED_LIGHT,
            letter_spacing=0.4,
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
            _bg_noise_overlay("metrics_grain_overlay", "url(#paper_grain)"),
            _metrics_header(),
            _metrics_tiles(),
            _metrics_chart(),
            _metrics_legend(),
            _shared_footer(3),
        ],
    )


__all__ = ["build_cover", "build_features", "build_metrics"]
