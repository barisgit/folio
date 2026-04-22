from __future__ import annotations

from collections.abc import Sequence

from theme import (
    BRAND_NAME_DARK,
    BRAND_NAME_LIGHT,
    BRAND_TAGLINE_DARK,
    BRAND_TAGLINE_LIGHT,
    CARD_BODY,
    CARD_TAG,
    CARD_TITLE,
    CHART_AXIS,
    FEATURE_BODY,
    FEATURE_INDEX,
    FEATURE_TAG,
    METRIC_DELTA,
    METRIC_LABEL,
    METRIC_VALUE,
)

from folio.dsl import (
    block,
    circle,
    clip_path,
    ellipse,
    group,
    image,
    measure_text,
    path,
    path_builder,
    polygon,
    polyline,
    rect,
    text,
    tokens,
)


def part(style_key: str, content: str) -> tuple[str, str]:
    return (style_key, content)


def build_rich_content(parts, normal_style, emphasis_style, *, prefix_id: str):
    from folio.dsl import tspan

    rich: list = []
    for index, (kind, text_value) in enumerate(parts, start=1):
        if kind == "emphasis":
            rich.append(
                tspan(
                    f"{prefix_id}_em_{index}",
                    text_value,
                    style=emphasis_style,
                )
            )
        else:
            rich.append(text_value)
    return rich, normal_style


def brand_chip(
    element_id: str,
    x_mm: float,
    y_mm: float,
    brand_name: str,
    brand_tagline: str,
    *,
    light: bool = True,
    padding_x_mm: float = 6.0,
    padding_y_mm: float = 4.0,
    disc_radius_mm: float = 3.6,
    disc_gap_mm: float = 3.0,
):
    name_style = BRAND_NAME_LIGHT if light else BRAND_NAME_DARK
    tagline_style = BRAND_TAGLINE_LIGHT if light else BRAND_TAGLINE_DARK
    name_metrics = measure_text(brand_name, style=name_style)
    tagline_metrics = measure_text(brand_tagline, style=tagline_style)
    label_width = max(name_metrics.width_mm, tagline_metrics.width_mm)
    block_height = name_metrics.height_mm + tagline_metrics.height_mm + 1.8
    chip_height = max(block_height + 2 * padding_y_mm, disc_radius_mm * 2 + 2.0)
    chip_width = padding_x_mm + disc_radius_mm * 2 + disc_gap_mm + label_width + padding_x_mm

    disc_cx = x_mm + padding_x_mm + disc_radius_mm
    disc_cy = y_mm + chip_height / 2
    label_x = disc_cx + disc_radius_mm + disc_gap_mm
    block_top = y_mm + (chip_height - block_height) / 2
    name_y = block_top + name_metrics.height_mm * 0.76
    tagline_y = name_y + 4.6

    frame_fill = tokens.WHITE if light else tokens.INK
    frame_opacity = 0.08 if light else 0.04
    disc_inner = tokens.deep_navy if light else tokens.WHITE

    return (
        group(
            element_id,
            "Brand Chip",
            rect(
                f"{element_id}_frame",
                x_mm,
                y_mm,
                chip_width,
                chip_height,
                fill=frame_fill,
                fill_opacity=frame_opacity,
                rx_mm=chip_height / 2,
                ry_mm=chip_height / 2,
            ),
            circle(
                f"{element_id}_disc",
                disc_cx,
                disc_cy,
                disc_radius_mm,
                fill=tokens.ACCENT,
            ),
            circle(
                f"{element_id}_disc_inner",
                disc_cx,
                disc_cy,
                disc_radius_mm * 0.42,
                fill=disc_inner,
            ),
            text(f"{element_id}_name", label_x, name_y, brand_name, style=name_style),
            text(
                f"{element_id}_tagline",
                label_x,
                tagline_y,
                brand_tagline,
                style=tagline_style,
            ),
        ),
        chip_width,
        chip_height,
    )


def counter_pill(
    element_id: str,
    right_x_mm: float,
    y_mm: float,
    label: str,
    *,
    light: bool = True,
    padding_x_mm: float = 6.0,
    padding_y_mm: float = 3.0,
):
    style = BRAND_NAME_LIGHT if light else BRAND_NAME_DARK
    from theme import COUNTER_MONO_DARK, COUNTER_MONO_LIGHT

    style = COUNTER_MONO_LIGHT if light else COUNTER_MONO_DARK
    metrics = measure_text(label, style=style)
    pill_w = metrics.width_mm + 2 * padding_x_mm
    pill_h = metrics.height_mm + 2 * padding_y_mm
    x_mm = right_x_mm - pill_w
    frame_fill = tokens.WHITE if light else tokens.INK
    frame_opacity = 0.08 if light else 0.04
    return group(
        element_id,
        "Counter Pill",
        rect(
            f"{element_id}_frame",
            x_mm,
            y_mm,
            pill_w,
            pill_h,
            fill=frame_fill,
            fill_opacity=frame_opacity,
            rx_mm=pill_h / 2,
            ry_mm=pill_h / 2,
        ),
        text(
            f"{element_id}_label",
            x_mm + pill_w / 2,
            y_mm + pill_h / 2 + metrics.height_mm * 0.3,
            label,
            style=style,
            anchor="middle",
        ),
    )


def corner_ticks(
    element_id: str,
    x_mm: float,
    y_mm: float,
    width_mm: float,
    height_mm: float,
    *,
    color: str,
    tick_mm: float = 3.2,
    stroke_mm: float = 0.25,
    opacity: float = 0.45,
):
    parts = [
        ((x_mm, y_mm + tick_mm), (x_mm, y_mm), (x_mm + tick_mm, y_mm)),
        (
            (x_mm + width_mm - tick_mm, y_mm),
            (x_mm + width_mm, y_mm),
            (x_mm + width_mm, y_mm + tick_mm),
        ),
        (
            (x_mm + width_mm, y_mm + height_mm - tick_mm),
            (x_mm + width_mm, y_mm + height_mm),
            (x_mm + width_mm - tick_mm, y_mm + height_mm),
        ),
        (
            (x_mm + tick_mm, y_mm + height_mm),
            (x_mm, y_mm + height_mm),
            (x_mm, y_mm + height_mm - tick_mm),
        ),
    ]
    return group(
        element_id,
        "Corner Ticks",
        *[
            polyline(
                f"{element_id}_tick_{index}",
                list(points),
                fill="none",
                stroke=color,
                stroke_width=stroke_mm,
                stroke_opacity=opacity,
            )
            for index, points in enumerate(parts, start=1)
        ],
    )


def numbered_feature(
    index: int,
    x_mm: float,
    y_mm: float,
    width_mm: float,
    index_label: str,
    tag: str,
    body_text: str,
):
    column = block(f"feature_{index}", at=(x_mm, y_mm))
    return column.layer(
        f"Feature {index}",
        column.rect("bar", 0, 0, 16.0, 0.7, fill=tokens.ACCENT),
        column.text("index", 0, 6.0, index_label, style=FEATURE_INDEX),
        column.text("tag", 0, 13.5, tag, style=FEATURE_TAG),
        column.wrapped_text(
            "body",
            0,
            20.0,
            body_text,
            width_mm=width_mm,
            line_step_mm=3.9,
            max_lines=4,
            style=FEATURE_BODY,
        ),
    )


def rounded_photo(
    element_id: str,
    x_mm: float,
    y_mm: float,
    width_mm: float,
    height_mm: float,
    reference: str,
    *,
    radius_mm: float = 4.0,
    halo_offset_mm: float = 3.0,
    halo_color: str = tokens.ACCENT,
    halo_opacity: float = 0.35,
    shadow_filter: str = "url(#hero_shadow)",
    show_frame: bool = True,
):
    clip_rect = rect(
        f"{element_id}_clip_rect",
        x_mm,
        y_mm,
        width_mm,
        height_mm,
        rx_mm=radius_mm,
        ry_mm=radius_mm,
        fill="white",
    )
    clip = clip_path(f"{element_id}_clip", clip_rect)
    children = [
        rect(
            f"{element_id}_halo",
            x_mm + halo_offset_mm,
            y_mm + halo_offset_mm,
            width_mm,
            height_mm,
            fill=halo_color,
            fill_opacity=halo_opacity,
            rx_mm=radius_mm,
            ry_mm=radius_mm,
        ),
        image(
            f"{element_id}_photo",
            reference,
            x_mm,
            y_mm,
            width_mm,
            height_mm,
            clip=clip,
            filter=shadow_filter,
            preserveAspectRatio="xMidYMid slice",
        ),
    ]
    if show_frame:
        children.append(
            rect(
                f"{element_id}_frame",
                x_mm,
                y_mm,
                width_mm,
                height_mm,
                fill="none",
                stroke=tokens.WHITE,
                stroke_width=0.4,
                stroke_opacity=0.2,
                rx_mm=radius_mm,
                ry_mm=radius_mm,
            )
        )
    return group(element_id, "Rounded Photo", *children)


def content_card(
    index: int,
    x_mm: float,
    y_mm: float,
    width_mm: float,
    height_mm: float,
    icon_reference: str,
    tag: str,
    title: str,
    body_text: str,
):
    card = block(f"card_{index}", at=(x_mm, y_mm))
    icon_size_mm = 9.0
    chip_cx = 12.0
    chip_cy = 14.0
    chip_r = 7.2
    return card.layer(
        f"Card {index}",
        card.rect(
            "panel",
            0,
            0,
            width_mm,
            height_mm,
            fill=tokens.WHITE,
            stroke=tokens.LINE,
            stroke_width=0.3,
            rx_mm=3.2,
            ry_mm=3.2,
            filter="url(#card_shadow)",
        ),
        card.rect(
            "accent",
            0,
            0,
            1.6,
            height_mm,
            fill=tokens.ACCENT,
            rx_mm=0.8,
            ry_mm=0.8,
        ),
        card.ellipse("chip_outer", chip_cx, chip_cy, chip_r, chip_r, fill=tokens.mist),
        card.ellipse(
            "chip_ring",
            chip_cx,
            chip_cy,
            chip_r + 1.4,
            chip_r + 1.4,
            fill="none",
            stroke=tokens.ACCENT,
            stroke_width=0.3,
            stroke_opacity=0.4,
        ),
        card.image(
            "icon",
            icon_reference,
            chip_cx - icon_size_mm / 2,
            chip_cy - icon_size_mm / 2,
            icon_size_mm,
            icon_size_mm,
        ),
        card.text("tag", 24.0, 11.0, tag, style=CARD_TAG),
        card.text("title", 24.0, 18.0, title, style=CARD_TITLE),
        card.wrapped_text(
            "body",
            7.0,
            30.0,
            body_text,
            width_mm=width_mm - 14.0,
            line_step_mm=4.1,
            max_lines=5,
            style=CARD_BODY,
        ),
    )


def metric_tile(
    index: int,
    x_mm: float,
    y_mm: float,
    width_mm: float,
    height_mm: float,
    label: str,
    value: str,
    delta: str,
):
    tile = block(f"metric_{index}", at=(x_mm, y_mm))
    return tile.layer(
        f"Metric {index}",
        tile.rect(
            "panel",
            0,
            0,
            width_mm,
            height_mm,
            fill=tokens.WHITE,
            stroke=tokens.LINE,
            stroke_width=0.3,
            rx_mm=3.0,
            ry_mm=3.0,
            filter="url(#tile_shadow)",
        ),
        tile.rect(
            "accent",
            0,
            0,
            width_mm,
            1.4,
            fill=tokens.ACCENT,
            rx_mm=3.0,
            ry_mm=3.0,
        ),
        tile.text("label", 8.0, 12.0, label, style=METRIC_LABEL),
        tile.text("value", 8.0, 32.0, value, style=METRIC_VALUE),
        tile.text("delta", 8.0, 40.0, delta, style=METRIC_DELTA),
    )


def sparkline_chart(
    element_id: str,
    x_mm: float,
    y_mm: float,
    width_mm: float,
    height_mm: float,
    values: Sequence[float],
    *,
    peak_index: int | None = None,
    peak_label: str | None = None,
):
    if len(values) < 2:
        raise ValueError("sparkline requires at least two values")
    lo = min(values)
    hi = max(values)
    if hi == lo:
        hi = lo + 1.0
    step_x_mm = width_mm / (len(values) - 1)

    def point(i: int, v: float) -> tuple[float, float]:
        px = x_mm + i * step_x_mm
        py = y_mm + height_mm - ((v - lo) / (hi - lo)) * height_mm
        return (round(px, 3), round(py, 3))

    points = [point(i, v) for i, v in enumerate(values)]

    area_builder = (
        path_builder().move_to(points[0][0], y_mm + height_mm).line_to(points[0][0], points[0][1])
    )
    for px, py in points[1:]:
        area_builder = area_builder.line_to(px, py)
    area_builder = area_builder.line_to(points[-1][0], y_mm + height_mm).close()

    grid_lines = [
        polyline(
            f"{element_id}_grid_top",
            [(x_mm, y_mm), (x_mm + width_mm, y_mm)],
            fill="none",
            stroke=tokens.LINE,
            stroke_width=0.25,
            stroke_dasharray="1.0 1.6",
        ),
        polyline(
            f"{element_id}_grid_mid",
            [
                (x_mm, y_mm + height_mm / 2),
                (x_mm + width_mm, y_mm + height_mm / 2),
            ],
            fill="none",
            stroke=tokens.LINE,
            stroke_width=0.25,
            stroke_dasharray="1.0 1.6",
        ),
    ]
    baseline = polyline(
        f"{element_id}_baseline",
        [(x_mm, y_mm + height_mm), (x_mm + width_mm, y_mm + height_mm)],
        fill="none",
        stroke=tokens.MUTED,
        stroke_width=0.35,
    )
    area = path(
        f"{element_id}_area",
        area_builder.build(),
        fill="url(#chart_area_gradient)",
        opacity=0.9,
    )
    line_element = polyline(
        f"{element_id}_line",
        points,
        fill="none",
        stroke=tokens.ACCENT,
        stroke_width=1.6,
        stroke_linejoin="round",
        stroke_linecap="round",
    )
    markers = [
        ellipse(
            f"{element_id}_point_{idx}",
            px,
            py,
            0.9,
            0.9,
            fill=tokens.WHITE,
            stroke=tokens.ACCENT,
            stroke_width=0.8,
        )
        for idx, (px, py) in enumerate(points, start=1)
    ]

    overlays: list = []
    if peak_index is not None and peak_label is not None and 0 <= peak_index < len(points):
        peak_x, peak_y = points[peak_index]
        label_metrics = measure_text(peak_label, size_pt=7.0, weight=700, letter_spacing=0.4)
        chip_w = label_metrics.width_mm + 6.0
        chip_h = label_metrics.height_mm + 4.0
        place_above = peak_y - chip_h - 6.0 > y_mm
        chip_y = peak_y - chip_h - 4.0 if place_above else peak_y + 4.0
        chip_x = peak_x - chip_w / 2
        chip_x = max(x_mm, min(chip_x, x_mm + width_mm - chip_w))
        tail_tip_y = chip_y + chip_h + 1.6 if place_above else chip_y - 1.6
        tail_base_y = chip_y + chip_h if place_above else chip_y
        overlays.extend(
            [
                polyline(
                    f"{element_id}_peak_line",
                    [(peak_x, peak_y + 2.0), (peak_x, y_mm + height_mm)],
                    fill="none",
                    stroke=tokens.ACCENT,
                    stroke_width=0.4,
                    stroke_dasharray="1.0 1.2",
                ),
                ellipse(
                    f"{element_id}_peak_marker",
                    peak_x,
                    peak_y,
                    1.7,
                    1.7,
                    fill=tokens.ACCENT,
                    stroke=tokens.WHITE,
                    stroke_width=0.8,
                ),
                rect(
                    f"{element_id}_peak_chip",
                    chip_x,
                    chip_y,
                    chip_w,
                    chip_h,
                    fill=tokens.INK,
                    rx_mm=1.2,
                    ry_mm=1.2,
                ),
                polygon(
                    f"{element_id}_peak_chip_tail",
                    [
                        (peak_x - 1.3, tail_base_y),
                        (peak_x + 1.3, tail_base_y),
                        (peak_x, tail_tip_y),
                    ],
                    fill=tokens.INK,
                ),
                text(
                    f"{element_id}_peak_label",
                    chip_x + chip_w / 2,
                    chip_y + chip_h - 1.4,
                    peak_label,
                    size_pt=7.0,
                    weight=700,
                    fill=tokens.WHITE,
                    anchor="middle",
                    letter_spacing=0.4,
                ),
            ]
        )

    return group(
        element_id,
        "Sparkline",
        *grid_lines,
        baseline,
        area,
        line_element,
        *markers,
        *overlays,
    )


def chart_axis_labels(
    element_id: str, labels: Sequence[str], x_mm: float, y_mm: float, width_mm: float
):
    if len(labels) < 2:
        return []
    step = width_mm / (len(labels) - 1)
    return [
        CHART_AXIS(
            f"{element_id}_label_{index}",
            round(x_mm + index * step, 3),
            y_mm,
            label,
            anchor="middle",
        )
        for index, label in enumerate(labels)
    ]


__all__ = [
    "brand_chip",
    "build_rich_content",
    "chart_axis_labels",
    "content_card",
    "corner_ticks",
    "counter_pill",
    "metric_tile",
    "numbered_feature",
    "part",
    "rounded_photo",
    "sparkline_chart",
]
