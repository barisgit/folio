from __future__ import annotations

import base64
import html
import mimetypes
from collections.abc import Mapping, Sequence
from pathlib import Path

from folio.core.render import tokens

_DATA_URI_CACHE: dict[Path, str] = {}


def m(value_mm: float) -> float:
    return round(value_mm * tokens.MM_TO_PT, 2)


def pt_to_mm(value_pt: float) -> float:
    return round(value_pt * tokens.PT_TO_MM, 2)


def escape_text(value: str) -> str:
    return html.escape(value, quote=False)


def _attrs(attrs: Mapping[str, object]) -> str:
    parts: list[str] = []
    for key, value in attrs.items():
        if value is None:
            continue
        parts.append(f' {key}="{value}"')
    return "".join(parts)


def _points_attr(points_mm: Sequence[tuple[float, float]]) -> str:
    return " ".join(f"{m(x_mm)},{m(y_mm)}" for x_mm, y_mm in points_mm)


def svg_open(
    width_mm: float = tokens.A4_WIDTH_MM,
    height_mm: float = tokens.A4_HEIGHT_MM,
) -> str:
    return (
        '<?xml version="1.0" encoding="UTF-8" standalone="no"?>\n'
        '<svg xmlns="http://www.w3.org/2000/svg"\n'
        '     xmlns:xlink="http://www.w3.org/1999/xlink"\n'
        '     xmlns:inkscape="http://www.inkscape.org/namespaces/inkscape"\n'
        f'     width="{width_mm:g}mm" height="{height_mm:g}mm"\n'
        f'     viewBox="0 0 {m(width_mm)} {m(height_mm)}"\n'
        f'     font-family="{tokens.DEFAULT_FONT_FAMILY}">\n'
    )


def group(group_id: str, label: str, content: str, **attrs: object) -> str:
    merged = {"id": group_id, "inkscape:label": label, **attrs}
    return f"<g{_attrs(merged)}>\n{content}\n</g>\n"


def rect_mm(
    element_id: str | None,
    x_mm: float,
    y_mm: float,
    width_mm: float,
    height_mm: float,
    *,
    fill: str,
    **attrs: object,
) -> str:
    merged: dict[str, object] = {
        "id": element_id,
        "x": m(x_mm),
        "y": m(y_mm),
        "width": m(width_mm),
        "height": m(height_mm),
        "fill": fill,
        **attrs,
    }
    return f"<rect{_attrs(merged)}/>"


def circle_mm(
    element_id: str | None,
    cx_mm: float,
    cy_mm: float,
    r_mm: float,
    *,
    fill: str,
    **attrs: object,
) -> str:
    merged = {"id": element_id, "cx": m(cx_mm), "cy": m(cy_mm), "r": m(r_mm), "fill": fill, **attrs}
    return f"<circle{_attrs(merged)}/>"


def ellipse_mm(
    element_id: str | None,
    cx_mm: float,
    cy_mm: float,
    rx_mm: float,
    ry_mm: float,
    *,
    fill: str,
    **attrs: object,
) -> str:
    merged = {
        "id": element_id,
        "cx": m(cx_mm),
        "cy": m(cy_mm),
        "rx": m(rx_mm),
        "ry": m(ry_mm),
        "fill": fill,
        **attrs,
    }
    return f"<ellipse{_attrs(merged)}/>"


def path(element_id: str | None, d: str, **attrs: object) -> str:
    merged = {"id": element_id, "d": d, **attrs}
    return f"<path{_attrs(merged)}/>"


def polygon_mm(
    element_id: str | None,
    points_mm: Sequence[tuple[float, float]],
    **attrs: object,
) -> str:
    merged = {"id": element_id, "points": _points_attr(points_mm), **attrs}
    return f"<polygon{_attrs(merged)}/>"


def polyline_mm(
    element_id: str | None,
    points_mm: Sequence[tuple[float, float]],
    **attrs: object,
) -> str:
    merged = {"id": element_id, "points": _points_attr(points_mm), **attrs}
    return f"<polyline{_attrs(merged)}/>"


def line_mm(
    element_id: str | None,
    x1_mm: float,
    y1_mm: float,
    x2_mm: float,
    y2_mm: float,
    **attrs: object,
) -> str:
    merged = {
        "id": element_id,
        "x1": m(x1_mm),
        "y1": m(y1_mm),
        "x2": m(x2_mm),
        "y2": m(y2_mm),
        **attrs,
    }
    return f"<line{_attrs(merged)}/>"


def _data_uri(asset_path: Path) -> str:
    if asset_path in _DATA_URI_CACHE:
        return _DATA_URI_CACHE[asset_path]

    mime = mimetypes.guess_type(str(asset_path))[0] or "image/png"
    data = base64.b64encode(asset_path.read_bytes()).decode("ascii")
    uri = f"data:{mime};base64,{data}"
    _DATA_URI_CACHE[asset_path] = uri
    return uri


def image_mm(
    element_id: str | None,
    asset_path: Path,
    x_mm: float,
    y_mm: float,
    width_mm: float,
    height_mm: float | None = None,
    **attrs: object,
) -> str:
    href = _data_uri(asset_path)
    merged: dict[str, object] = {
        "id": element_id,
        "href": href,
        "xlink:href": href,
        "x": m(x_mm),
        "y": m(y_mm),
        "width": m(width_mm),
        "preserveAspectRatio": "xMidYMid meet",
        **attrs,
    }
    if height_mm is not None:
        merged["height"] = m(height_mm)
    return f"<image{_attrs(merged)}/>"


def text_mm(
    element_id: str | None,
    x_mm: float,
    y_mm: float,
    text: str,
    *,
    size_pt: float | str,
    weight: int = 400,
    fill: str = "#ffffff",
    letter_spacing: float | str | None = None,
    anchor: str = "start",
    family: str | None = None,
    italic: bool = False,
    font_style: str | None = None,
    raw: bool = False,
    **attrs: object,
) -> str:
    merged: dict[str, object] = {
        "id": element_id,
        "x": m(x_mm),
        "y": m(y_mm),
        "font-size": size_pt,
        "font-weight": weight,
        "fill": fill,
        **attrs,
    }
    if letter_spacing is not None:
        merged["letter-spacing"] = letter_spacing
    if anchor != "start":
        merged["text-anchor"] = anchor
    if family is not None:
        merged["font-family"] = family
    if font_style is None and italic:
        font_style = "italic"
    if font_style is not None:
        merged["font-style"] = font_style
    inner = text if raw else escape_text(text)
    return f"<text{_attrs(merged)}>{inner}</text>"


def tspan(element_id: str | None, text: str, *, raw: bool = False, **attrs: object) -> str:
    merged = {"id": element_id, **attrs} if element_id is not None else dict(attrs)
    inner = text if raw else escape_text(text)
    return f"<tspan{_attrs(merged)}>{inner}</tspan>"


def multiline_text_mm(
    element_id: str | None,
    x_mm: float,
    y_mm: float,
    lines: Sequence[str],
    *,
    line_step_mm: float,
    size_pt: float,
    weight: int = 400,
    fill: str = "#ffffff",
    letter_spacing: float | None = None,
    anchor: str = "start",
    family: str | None = None,
    **attrs: object,
) -> str:
    merged: dict[str, object] = {
        "id": element_id,
        "x": m(x_mm),
        "y": m(y_mm),
        "font-size": size_pt,
        "font-weight": weight,
        "fill": fill,
        **attrs,
    }
    if letter_spacing is not None:
        merged["letter-spacing"] = letter_spacing
    if anchor != "start":
        merged["text-anchor"] = anchor
    if family is not None:
        merged["font-family"] = family

    tspans = []
    for index, line in enumerate(lines):
        y_value = m(y_mm + (index * line_step_mm))
        tspans.append(f'<tspan x="{m(x_mm)}" y="{y_value}">{escape_text(line)}</tspan>')
    return f"<text{_attrs(merged)}>{''.join(tspans)}</text>"


def grid_lines_mm(
    element_id: str | None,
    *,
    width_mm: float = tokens.A4_WIDTH_MM,
    height_mm: float = tokens.A4_HEIGHT_MM,
    step_mm: float = 6.35,
    stroke: str = "#ffffff",
    stroke_opacity: float = 0.05,
    stroke_width: float = 0.25,
) -> str:
    parts: list[str] = []
    x = step_mm
    while x < width_mm:
        parts.append(f"M{m(x)} 0 V{m(height_mm)}")
        x += step_mm

    y = step_mm
    while y < height_mm:
        parts.append(f"M0 {m(y)} H{m(width_mm)}")
        y += step_mm

    return path(
        element_id,
        " ".join(parts),
        fill="none",
        stroke=stroke,
        **{"stroke-opacity": stroke_opacity, "stroke-width": stroke_width},
    )
