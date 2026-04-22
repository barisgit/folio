from __future__ import annotations

from collections.abc import Sequence

from theme import (
    CARD_BODY,
    CARD_INDEX,
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
    clip_path,
    ellipse,
    group,
    image,
    markup,
    path,
    path_builder,
    polygon,
    polyline,
    rect,
    text,
    tokens,
    wrapped_text,
)


def corner_ticks(element_id: str, x_mm: float, y_mm: float, width_mm: float, height_mm: float, *, color: str, tick_mm: float = 3.2, stroke_mm: float = 0.25):
    parts = [
        ((x_mm, y_mm + tick_mm), (x_mm, y_mm), (x_mm + tick_mm, y_mm)),
        ((x_mm + width_mm - tick_mm, y_mm), (x_mm + width_mm, y_mm), (x_mm + width_mm, y_mm + tick_mm)),
        ((x_mm + width_mm, y_mm + height_mm - tick_mm), (x_mm + width_mm, y_mm + height_mm), (x_mm + width_mm - tick_mm, y_mm + height_mm)),
        ((x_mm + tick_mm, y_mm + height_mm), (x_mm, y_mm + height_mm), (x_mm, y_mm + height_mm - tick_mm)),
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
                stroke_opacity=0.55,
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
        column.rect("bar", 0, 0, 14.0, 0.6, fill=tokens.ACCENT),
        column.text("index", 0, 5.5, index_label, style=FEATURE_INDEX),
        column.text("tag", 0, 12.0, tag, style=FEATURE_TAG),
        wrapped_text(
            column.id("body"),
            column.x(0),
            column.y(18.0),
            body_text,
            width_mm=width_mm,
            line_step_mm=3.8,
            max_lines=3,
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
    return group(
        element_id,
        "Rounded Photo",
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
        rect(
            f"{element_id}_frame",
            x_mm,
            y_mm,
            width_mm,
            height_mm,
            fill="none",
            stroke=tokens.WHITE,
            stroke_width=0.4,
            stroke_opacity=0.18,
            rx_mm=radius_mm,
            ry_mm=radius_mm,
        ),
    )


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
    icon_size_mm = 7.5
    chip_cx = 11.0
    chip_cy = 13.0
    chip_r = 6.2
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
            rx_mm=2.8,
            ry_mm=2.8,
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
        ellipse(
            f"card_{index}_chip_outer",
            card.x(chip_cx),
            card.y(chip_cy),
            chip_r,
            chip_r,
            fill=tokens.mist,
        ),
        ellipse(
            f"card_{index}_chip_ring",
            card.x(chip_cx),
            card.y(chip_cy),
            chip_r + 1.2,
            chip_r + 1.2,
            fill="none",
            stroke=tokens.ACCENT,
            stroke_width=0.3,
            stroke_opacity=0.3,
        ),
        image(
            f"card_{index}_icon",
            icon_reference,
            card.x(chip_cx - icon_size_mm / 2),
            card.y(chip_cy - icon_size_mm / 2),
            icon_size_mm,
            icon_size_mm,
        ),
        card.text("tag", 21.5, 10.5, tag, style=CARD_TAG),
        card.text("title", 21.5, 17.0, title, style=CARD_TITLE),
        wrapped_text(
            card.id("body"),
            card.x(6.0),
            card.y(27.0),
            body_text,
            width_mm=width_mm - 12.0,
            line_step_mm=4.0,
            max_lines=4,
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
            rx_mm=2.6,
            ry_mm=2.6,
            filter="url(#tile_shadow)",
        ),
        tile.rect(
            "accent",
            0,
            0,
            width_mm,
            1.2,
            fill=tokens.ACCENT,
            rx_mm=2.6,
            ry_mm=2.6,
        ),
        tile.text("label", 6.0, 10.0, label, style=METRIC_LABEL),
        tile.text("value", 6.0, 26.0, value, style=METRIC_VALUE),
        tile.text("delta", 6.0, 33.5, delta, style=METRIC_DELTA),
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
        path_builder()
        .move_to(points[0][0], y_mm + height_mm)
        .line_to(points[0][0], points[0][1])
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
            0.85,
            0.85,
            fill=tokens.WHITE,
            stroke=tokens.ACCENT,
            stroke_width=0.8,
        )
        for idx, (px, py) in enumerate(points, start=1)
    ]

    overlays: list = []
    if peak_index is not None and peak_label is not None and 0 <= peak_index < len(points):
        peak_x, peak_y = points[peak_index]
        overlays.append(
            polyline(
                f"{element_id}_peak_line",
                [(peak_x, peak_y + 2.2), (peak_x, y_mm + height_mm)],
                fill="none",
                stroke=tokens.ACCENT,
                stroke_width=0.4,
                stroke_dasharray="1.0 1.2",
            )
        )
        overlays.append(
            ellipse(
                f"{element_id}_peak_marker",
                peak_x,
                peak_y,
                1.6,
                1.6,
                fill=tokens.ACCENT,
                stroke=tokens.WHITE,
                stroke_width=0.8,
            )
        )
        overlays.append(
            rect(
                f"{element_id}_peak_chip",
                peak_x - 16.0,
                peak_y - 10.0,
                32.0,
                6.0,
                fill=tokens.INK,
                rx_mm=1.0,
                ry_mm=1.0,
            )
        )
        overlays.append(
            text(
                f"{element_id}_peak_label",
                peak_x,
                peak_y - 5.8,
                peak_label,
                size_pt=6.8,
                weight=700,
                fill=tokens.WHITE,
                anchor="middle",
                letter_spacing=0.4,
            )
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


def chart_axis_labels(element_id: str, labels: Sequence[str], x_mm: float, y_mm: float, width_mm: float):
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
    "chart_axis_labels",
    "content_card",
    "corner_ticks",
    "metric_tile",
    "numbered_feature",
    "rounded_photo",
    "sparkline_chart",
]
