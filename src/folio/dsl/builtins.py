from __future__ import annotations

import math
from collections import defaultdict
from collections.abc import Iterable, Sequence
from dataclasses import dataclass, field
from typing import Any

from folio.dsl.model import Asset, DefNode, Document, Element, ElementKind, Markup, Page, TextSpan
from folio.dsl.styles import TextStyle, coerce_text_style, merge_text_style_attrs
from folio.render import tokens as render_tokens
from folio.render.tokens import MM_TO_PT, PT_TO_MM
from folio.vendor.qrcodegen import QrCode

_AUTO_IDS: defaultdict[str, int] = defaultdict(int)
_QR_ECC = {
    "L": QrCode.Ecc.LOW,
    "M": QrCode.Ecc.MEDIUM,
    "Q": QrCode.Ecc.QUARTILE,
    "H": QrCode.Ecc.HIGH,
}


def reset_auto_ids() -> None:
    _AUTO_IDS.clear()


def _element_id(kind: str, element_id: str | None) -> str:
    if element_id:
        return element_id
    _AUTO_IDS[kind] += 1
    return f"{kind}_{_AUTO_IDS[kind]}"


def _coerce_variadic_children(children: tuple[Any, ...]) -> tuple[Any, ...]:
    if len(children) != 1:
        return children
    child = children[0]
    if isinstance(child, Element | DefNode):
        return children
    if isinstance(child, Iterable) and not isinstance(child, str | bytes | Markup):
        return tuple(child)
    return children


def _coerce_elements(children: Iterable[Element], *, source: str) -> tuple[Element, ...]:
    coerced = tuple(children)
    if not all(isinstance(child, Element) for child in coerced):
        raise TypeError(f"{source} children must be Element instances")
    return coerced


def _coerce_def_children(children: Iterable[DefNode | Element]) -> tuple[DefNode | Element, ...]:
    coerced = tuple(children)
    if not all(isinstance(child, DefNode | Element) for child in coerced):
        raise TypeError("defs children must be DefNode or Element instances")
    return coerced


def _coerce_defs(
    defs: str | Markup | Sequence[DefNode] | None,
) -> str | Markup | tuple[DefNode, ...]:
    if defs is None:
        return ()
    if isinstance(defs, str | Markup):
        return defs
    coerced = tuple(defs)
    if not all(isinstance(node, DefNode) for node in coerced):
        raise TypeError("page() defs must be a Markup/string or a sequence of DefNode instances")
    return coerced


def _coerce_text_content(
    content: str | Markup | Sequence[str | Markup | TextSpan], *, source: str
) -> str | Markup | tuple[str | Markup | TextSpan, ...]:
    if isinstance(content, str | Markup):
        return content
    if isinstance(content, Sequence) and not isinstance(content, str | bytes):
        coerced = tuple(content)
        if not all(isinstance(part, str | Markup | TextSpan) for part in coerced):
            raise TypeError(
                f"{source} content must contain only strings, Markup, or TextSpan instances"
            )
        return coerced
    raise TypeError(
        f"{source} content must be a string, Markup, or a sequence of "
        "strings/Markup/TextSpan"
    )


ELLIPSIS = "…"
_DEFAULT_WRAP_WIDTH_RATIO = 0.53
_DEFAULT_LINE_HEIGHT = 1.35



def _default_line_step_mm(size_pt: float) -> float:
    return round(size_pt * PT_TO_MM * _DEFAULT_LINE_HEIGHT, 2)



def _measure_text_mm(text: str, *, size_pt: float, letter_spacing: float | None = None) -> float:
    if not text:
        return 0.0
    glyph_width_mm = size_pt * PT_TO_MM * _DEFAULT_WRAP_WIDTH_RATIO
    letter_spacing_mm = 0.0 if letter_spacing is None else float(letter_spacing) * PT_TO_MM
    return (len(text) * glyph_width_mm) + (max(0, len(text) - 1) * letter_spacing_mm)



def _truncate_to_width(
    text: str,
    *,
    width_mm: float,
    size_pt: float,
    letter_spacing: float | None,
    use_ellipsis: bool,
) -> str:
    candidate = text.strip()
    suffix = ELLIPSIS if use_ellipsis and candidate else ""
    while candidate and _measure_text_mm(
        f"{candidate}{suffix}",
        size_pt=size_pt,
        letter_spacing=letter_spacing,
    ) > width_mm:
        candidate = candidate[:-1].rstrip()
    if not candidate:
        return ELLIPSIS if use_ellipsis else ""
    return f"{candidate}{suffix}"



def _wrap_plain_text(
    content: str,
    *,
    width_mm: float,
    size_pt: float,
    letter_spacing: float | None,
    max_lines: int | None,
    overflow: str,
) -> list[str]:
    if width_mm <= 0:
        raise TypeError("wrapped_text() width_mm must be positive")
    if max_lines is not None and max_lines <= 0:
        raise TypeError("wrapped_text() max_lines must be positive when provided")
    if overflow not in {"ellipsis", "clip"}:
        raise TypeError("wrapped_text() overflow must be 'ellipsis' or 'clip'")

    paragraphs = content.splitlines() or [content]
    lines: list[str] = []
    for paragraph in paragraphs:
        if paragraph.strip() == "":
            lines.append("")
            continue

        current = ""
        for word in paragraph.split():
            candidate = word if not current else f"{current} {word}"
            if _measure_text_mm(
                candidate,
                size_pt=size_pt,
                letter_spacing=letter_spacing,
            ) <= width_mm:
                current = candidate
                continue

            if current:
                lines.append(current)
                current = word
            else:
                lines.append(
                    _truncate_to_width(
                        word,
                        width_mm=width_mm,
                        size_pt=size_pt,
                        letter_spacing=letter_spacing,
                        use_ellipsis=False,
                    )
                )
                current = ""

        if current:
            lines.append(current)

    if max_lines is None or len(lines) <= max_lines:
        return lines

    truncated = lines[:max_lines]
    remaining_text = " ".join(line for line in lines[max_lines - 1 :] if line)
    truncated[-1] = _truncate_to_width(
        remaining_text or truncated[-1],
        width_mm=width_mm,
        size_pt=size_pt,
        letter_spacing=letter_spacing,
        use_ellipsis=overflow == "ellipsis",
    )
    return truncated


def _qr_path_data(
    qr_code: QrCode,
    *,
    x_mm: float,
    y_mm: float,
    size_mm: float,
    border_modules: int,
) -> str:
    module_count = qr_code.get_size() + (border_modules * 2)
    module_mm = size_mm / module_count
    parts: list[str] = []
    for y_index in range(qr_code.get_size()):
        run_start: int | None = None
        for x_index in range(qr_code.get_size() + 1):
            dark = qr_code.get_module(x_index, y_index)
            if dark and run_start is None:
                run_start = x_index
                continue
            if dark or run_start is None:
                continue

            x0_mm = x_mm + ((run_start + border_modules) * module_mm)
            x1_mm = x_mm + ((x_index + border_modules) * module_mm)
            y0_mm = y_mm + ((y_index + border_modules) * module_mm)
            y1_mm = y0_mm + module_mm
            parts.append(
                f"M{_pt(x0_mm)} {_pt(y0_mm)} "
                f"L{_pt(x1_mm)} {_pt(y0_mm)} "
                f"L{_pt(x1_mm)} {_pt(y1_mm)} "
                f"L{_pt(x0_mm)} {_pt(y1_mm)} Z"
            )
            run_start = None
    return " ".join(parts)


def _coerce_points_mm(
    points_mm: Sequence[tuple[float, float]] | Iterable[tuple[float, float]],
    *,
    source: str,
) -> tuple[tuple[float, float], ...]:
    points = tuple((float(x_mm), float(y_mm)) for x_mm, y_mm in points_mm)
    if not points:
        raise TypeError(f"{source} requires at least one point")
    return points



def _offset_mm_attr(attrs: dict[str, Any], key: str, delta: float) -> None:
    value = attrs.get(key)
    if value is not None:
        attrs[key] = value + delta



def _offset_xy_attrs(attrs: dict[str, Any], *, x_mm: float, y_mm: float) -> dict[str, Any]:
    adjusted = dict(attrs)
    _offset_mm_attr(adjusted, "x_mm", x_mm)
    _offset_mm_attr(adjusted, "y_mm", y_mm)
    return adjusted


@dataclass(slots=True)
class TransformBuilder:
    operations: list[str] = field(default_factory=list)
    origin_x_mm: float = 0.0
    origin_y_mm: float = 0.0

    def translate(self, x_mm: float = 0.0, y_mm: float = 0.0) -> TransformBuilder:
        self.operations.append(f"translate({_pt(x_mm)} {_pt(y_mm)})")
        return self

    def rotate(
        self,
        angle_deg: float,
        *,
        cx_mm: float | None = None,
        cy_mm: float | None = None,
    ) -> TransformBuilder:
        if cx_mm is None and cy_mm is None:
            self.operations.append(f"rotate({angle_deg:g})")
            return self
        if cx_mm is None or cy_mm is None:
            raise TypeError("TransformBuilder.rotate() requires both cx_mm and cy_mm")
        self.operations.append(
            f"rotate({angle_deg:g} {_pt(self.origin_x_mm + cx_mm)} {_pt(self.origin_y_mm + cy_mm)})"
        )
        return self

    def scale(self, sx: float, sy: float | None = None) -> TransformBuilder:
        if sy is None:
            self.operations.append(f"scale({sx:g})")
        else:
            self.operations.append(f"scale({sx:g} {sy:g})")
        return self

    def skew_x(self, angle_deg: float) -> TransformBuilder:
        self.operations.append(f"skewX({angle_deg:g})")
        return self

    def skew_y(self, angle_deg: float) -> TransformBuilder:
        self.operations.append(f"skewY({angle_deg:g})")
        return self

    def matrix(
        self,
        a: float,
        b: float,
        c: float,
        d: float,
        e_mm: float = 0.0,
        f_mm: float = 0.0,
    ) -> TransformBuilder:
        self.operations.append(
            f"matrix({a:g} {b:g} {c:g} {d:g} {_pt(e_mm)} {_pt(f_mm)})"
        )
        return self

    def build(self) -> str:
        return " ".join(self.operations)

    def __str__(self) -> str:
        return self.build()


@dataclass(slots=True)
class PathBuilder:
    commands: list[str] = field(default_factory=list)
    origin_x_mm: float = 0.0
    origin_y_mm: float = 0.0

    def _push(self, command: str, *values_mm: float) -> PathBuilder:
        if values_mm:
            serialized = " ".join(str(_pt(value_mm)) for value_mm in values_mm)
            self.commands.append(f"{command}{serialized}")
        else:
            self.commands.append(command)
        return self

    def move_to(self, x_mm: float, y_mm: float) -> PathBuilder:
        return self._push("M", self.origin_x_mm + x_mm, self.origin_y_mm + y_mm)

    def line_to(self, x_mm: float, y_mm: float) -> PathBuilder:
        return self._push("L", self.origin_x_mm + x_mm, self.origin_y_mm + y_mm)

    def horizontal_to(self, x_mm: float) -> PathBuilder:
        return self._push("H", self.origin_x_mm + x_mm)

    def vertical_to(self, y_mm: float) -> PathBuilder:
        return self._push("V", self.origin_y_mm + y_mm)

    def curve_to(
        self,
        c1x_mm: float,
        c1y_mm: float,
        c2x_mm: float,
        c2y_mm: float,
        x_mm: float,
        y_mm: float,
    ) -> PathBuilder:
        return self._push(
            "C",
            self.origin_x_mm + c1x_mm,
            self.origin_y_mm + c1y_mm,
            self.origin_x_mm + c2x_mm,
            self.origin_y_mm + c2y_mm,
            self.origin_x_mm + x_mm,
            self.origin_y_mm + y_mm,
        )

    def quad_to(self, cx_mm: float, cy_mm: float, x_mm: float, y_mm: float) -> PathBuilder:
        return self._push(
            "Q",
            self.origin_x_mm + cx_mm,
            self.origin_y_mm + cy_mm,
            self.origin_x_mm + x_mm,
            self.origin_y_mm + y_mm,
        )

    def arc_to(
        self,
        rx_mm: float,
        ry_mm: float,
        x_axis_rotation_deg: float,
        x_mm: float,
        y_mm: float,
        *,
        large_arc: bool = False,
        sweep: bool = True,
    ) -> PathBuilder:
        return self._push(
            "A",
            rx_mm,
            ry_mm,
            x_axis_rotation_deg,
            1.0 if large_arc else 0.0,
            1.0 if sweep else 0.0,
            self.origin_x_mm + x_mm,
            self.origin_y_mm + y_mm,
        )

    def close(self) -> PathBuilder:
        self.commands.append("Z")
        return self

    def build(self) -> str:
        return " ".join(self.commands)

    def __str__(self) -> str:
        return self.build()


@dataclass(frozen=True, slots=True)
class Block:
    prefix: str
    x_mm: float = 0.0
    y_mm: float = 0.0

    def id(self, suffix: str | None = None) -> str:
        if not suffix:
            return self.prefix
        return f"{self.prefix}_{suffix}"

    def x(self, value_mm: float) -> float:
        return self.x_mm + value_mm

    def y(self, value_mm: float) -> float:
        return self.y_mm + value_mm

    def point(self, x_mm: float, y_mm: float) -> tuple[float, float]:
        return (self.x(x_mm), self.y(y_mm))

    def scope(self, suffix: str, *, at: tuple[float, float] = (0.0, 0.0)) -> Block:
        child_x_mm, child_y_mm = at
        return Block(self.id(suffix), self.x(child_x_mm), self.y(child_y_mm))

    def rect(
        self,
        suffix: str,
        x_mm: float,
        y_mm: float,
        width_mm: float,
        height_mm: float,
        **attrs: Any,
    ) -> Element:
        return rect(self.id(suffix), self.x(x_mm), self.y(y_mm), width_mm, height_mm, **attrs)

    def circle(
        self,
        suffix: str,
        cx_mm: float,
        cy_mm: float,
        radius_mm: float,
        **attrs: Any,
    ) -> Element:
        return circle(self.id(suffix), self.x(cx_mm), self.y(cy_mm), radius_mm, **attrs)

    def ellipse(
        self,
        suffix: str,
        cx_mm: float,
        cy_mm: float,
        rx_mm: float,
        ry_mm: float,
        **attrs: Any,
    ) -> Element:
        return ellipse(self.id(suffix), self.x(cx_mm), self.y(cy_mm), rx_mm, ry_mm, **attrs)

    def polygon(
        self,
        suffix: str,
        points_mm: Sequence[tuple[float, float]],
        **attrs: Any,
    ) -> Element:
        return polygon(
            self.id(suffix),
            [self.point(x_mm, y_mm) for x_mm, y_mm in points_mm],
            **attrs,
        )

    def polyline(
        self,
        suffix: str,
        points_mm: Sequence[tuple[float, float]],
        **attrs: Any,
    ) -> Element:
        return polyline(
            self.id(suffix),
            [self.point(x_mm, y_mm) for x_mm, y_mm in points_mm],
            **attrs,
        )

    def text(
        self,
        suffix: str,
        x_mm: float,
        y_mm: float,
        content: str | Markup | Sequence[str | Markup | TextSpan],
        *,
        style: TextStyle | None = None,
        **attrs: Any,
    ) -> Element:
        return text(self.id(suffix), self.x(x_mm), self.y(y_mm), content, style=style, **attrs)

    def multiline(
        self,
        suffix: str,
        x_mm: float,
        y_mm: float,
        lines: Sequence[str | Markup | Sequence[str | Markup | TextSpan]],
        *,
        line_step_mm: float,
        style: TextStyle | None = None,
        **attrs: Any,
    ) -> Element:
        return multiline(
            self.id(suffix),
            self.x(x_mm),
            self.y(y_mm),
            lines,
            line_step_mm=line_step_mm,
            style=style,
            **attrs,
        )

    def wrapped_text(
        self,
        suffix: str,
        x_mm: float,
        y_mm: float,
        content: str,
        *,
        width_mm: float,
        line_step_mm: float | None = None,
        max_lines: int | None = None,
        overflow: str = "ellipsis",
        style: TextStyle | None = None,
        **attrs: Any,
    ) -> Element:
        return wrapped_text(
            self.id(suffix),
            self.x(x_mm),
            self.y(y_mm),
            content,
            width_mm=width_mm,
            line_step_mm=line_step_mm,
            max_lines=max_lines,
            overflow=overflow,
            style=style,
            **attrs,
        )

    def span(
        self,
        suffix: str,
        content: str | Markup | Sequence[str | Markup | TextSpan],
        *,
        style: TextStyle | None = None,
        **attrs: Any,
    ) -> TextSpan:
        return tspan(
            self.id(suffix),
            content,
            style=style,
            **_offset_xy_attrs(attrs, x_mm=self.x_mm, y_mm=self.y_mm),
        )

    def image(
        self,
        suffix: str,
        reference: str,
        x_mm: float,
        y_mm: float,
        width_mm: float,
        height_mm: float | None = None,
        **attrs: Any,
    ) -> Element:
        return image(
            self.id(suffix),
            reference,
            self.x(x_mm),
            self.y(y_mm),
            width_mm,
            height_mm,
            **attrs,
        )

    def qr(
        self,
        suffix: str,
        x_mm: float,
        y_mm: float,
        data: str | bytes,
        *,
        size_mm: float,
        ecc: str = "M",
        border_modules: int = 4,
        fill: str = render_tokens.INK,
        background_fill: str | None = None,
        **attrs: Any,
    ) -> Element:
        return qr(
            self.id(suffix),
            self.x(x_mm),
            self.y(y_mm),
            data,
            size_mm=size_mm,
            ecc=ecc,
            border_modules=border_modules,
            fill=fill,
            background_fill=background_fill,
            **attrs,
        )

    def line(
        self,
        suffix: str,
        x1_mm: float,
        y1_mm: float,
        x2_mm: float,
        y2_mm: float,
        **attrs: Any,
    ) -> Element:
        return line(
            self.id(suffix),
            self.x(x1_mm),
            self.y(y1_mm),
            self.x(x2_mm),
            self.y(y2_mm),
            **attrs,
        )

    def rule(
        self,
        suffix: str,
        x_mm: float,
        y_mm: float,
        width_mm: float,
        *,
        height_mm: float = 0.3,
        fill: str,
        opacity: float | None = None,
        **attrs: Any,
    ) -> Element:
        return rule(
            self.id(suffix),
            self.x(x_mm),
            self.y(y_mm),
            width_mm,
            height_mm=height_mm,
            fill=fill,
            opacity=opacity,
            **attrs,
        )

    def triangle(
        self,
        suffix: str,
        x_mm: float | None = None,
        y_mm: float | None = None,
        width_mm: float | None = None,
        height_mm: float | None = None,
        *,
        cx_mm: float | None = None,
        cy_mm: float | None = None,
        size_mm: float | None = None,
        direction: str = "right",
        **attrs: Any,
    ) -> Element:
        if cx_mm is not None or cy_mm is not None:
            return triangle(
                self.id(suffix),
                cx_mm=self.x(cx_mm or 0.0),
                cy_mm=self.y(cy_mm or 0.0),
                size_mm=size_mm,
                width_mm=width_mm,
                height_mm=height_mm,
                direction=direction,
                **attrs,
            )
        return triangle(
            self.id(suffix),
            x_mm=self.x(x_mm or 0.0),
            y_mm=self.y(y_mm or 0.0),
            width_mm=width_mm,
            height_mm=height_mm,
            direction=direction,
            **attrs,
        )

    def transform_builder(self) -> TransformBuilder:
        return TransformBuilder(origin_x_mm=self.x_mm, origin_y_mm=self.y_mm)

    def path_builder(self) -> PathBuilder:
        return PathBuilder(origin_x_mm=self.x_mm, origin_y_mm=self.y_mm)

    def path(self, suffix: str, d: str | PathBuilder, **attrs: Any) -> Element:
        return path(self.id(suffix), d, **attrs)

    def group(
        self,
        suffix: str,
        label: str,
        *children: Element,
        **attrs: Any,
    ) -> Element:
        return group(self.id(suffix), label, *children, **attrs)

    def layer(self, label: str, *children: Element, **attrs: Any) -> Element:
        return self.group("group", label, *children, **attrs)



def block(prefix: str, *, at: tuple[float, float] = (0.0, 0.0)) -> Block:
    x_mm, y_mm = at
    return Block(prefix=prefix, x_mm=x_mm, y_mm=y_mm)



def page(
    *children: Element,
    page_id: str,
    filename: str,
    page_number: int,
    width_mm: float = render_tokens.A4_WIDTH_MM,
    height_mm: float = render_tokens.A4_HEIGHT_MM,
    elements: Sequence[Element] | None = None,
    defs: str | Markup | Sequence[DefNode] | None = None,
    label: str | None = None,
    **attrs: Any,
) -> Page:
    if children and elements is not None:
        raise TypeError("page() accepts either positional elements or elements=[...], not both")
    if elements is None:
        if not children:
            raise TypeError("page() requires positional elements or elements=[...]")
        page_elements = _coerce_elements(
            _coerce_variadic_children(children), source="page()"
        )
    else:
        page_elements = _coerce_elements(elements, source="page()")
    return Page(
        page_number=page_number,
        page_id=page_id,
        filename=filename,
        elements=page_elements,
        width_mm=width_mm,
        height_mm=height_mm,
        defs=_coerce_defs(defs),
        label=label,
        attrs=dict(attrs),
    )


def rect(
    element_id: str | None,
    x_mm: float,
    y_mm: float,
    width_mm: float,
    height_mm: float,
    **attrs: Any,
) -> Element:
    return Element(
        kind=ElementKind.RECT,
        element_id=_element_id("rect", element_id),
        x_mm=x_mm,
        y_mm=y_mm,
        attrs={"width_mm": width_mm, "height_mm": height_mm, **attrs},
    )


def circle(
    element_id: str | None,
    cx_mm: float,
    cy_mm: float,
    radius_mm: float,
    **attrs: Any,
) -> Element:
    return Element(
        kind=ElementKind.CIRCLE,
        element_id=_element_id("circle", element_id),
        x_mm=cx_mm,
        y_mm=cy_mm,
        attrs={"radius_mm": radius_mm, **attrs},
    )


def ellipse(
    element_id: str | None,
    cx_mm: float,
    cy_mm: float,
    rx_mm: float,
    ry_mm: float,
    **attrs: Any,
) -> Element:
    return Element(
        kind=ElementKind.ELLIPSE,
        element_id=_element_id("ellipse", element_id),
        x_mm=cx_mm,
        y_mm=cy_mm,
        attrs={"rx_mm": rx_mm, "ry_mm": ry_mm, **attrs},
    )



def polygon(
    element_id: str | None,
    points_mm: Sequence[tuple[float, float]] | Iterable[tuple[float, float]],
    **attrs: Any,
) -> Element:
    return Element(
        kind=ElementKind.POLYGON,
        element_id=_element_id("polygon", element_id),
        content=_coerce_points_mm(points_mm, source="polygon()"),
        attrs=dict(attrs),
    )



def polyline(
    element_id: str | None,
    points_mm: Sequence[tuple[float, float]] | Iterable[tuple[float, float]],
    **attrs: Any,
) -> Element:
    return Element(
        kind=ElementKind.POLYLINE,
        element_id=_element_id("polyline", element_id),
        content=_coerce_points_mm(points_mm, source="polyline()"),
        attrs=dict(attrs),
    )



def text(
    element_id: str | None,
    x_mm: float,
    y_mm: float,
    content: str | Markup | Sequence[str | Markup | TextSpan],
    *,
    style: TextStyle | None = None,
    **attrs: Any,
) -> Element:
    if "raw" in attrs:
        raise TypeError("text() no longer accepts raw=...; use markup() for trusted raw content")
    coerce_text_style(style, source="text()")
    return Element(
        kind=ElementKind.TEXT,
        element_id=_element_id("text", element_id),
        x_mm=x_mm,
        y_mm=y_mm,
        content=_coerce_text_content(content, source="text()"),
        attrs=({"style": style, **attrs} if style is not None else dict(attrs)),
    )


def tspan(
    element_id: str | None,
    content: str | Markup | Sequence[str | Markup | TextSpan],
    *,
    style: TextStyle | None = None,
    **attrs: Any,
) -> TextSpan:
    if "raw" in attrs:
        raise TypeError("tspan() no longer accepts raw=...; use markup() for trusted raw content")
    coerce_text_style(style, source="tspan()")
    return TextSpan(
        element_id=element_id,
        content=_coerce_text_content(content, source="tspan()"),
        attrs=({"style": style, **attrs} if style is not None else dict(attrs)),
    )



def multiline(
    element_id: str | None,
    x_mm: float,
    y_mm: float,
    lines: Sequence[str | Markup | Sequence[str | Markup | TextSpan]],
    *,
    line_step_mm: float,
    style: TextStyle | None = None,
    **attrs: Any,
) -> Element:
    return text(
        element_id,
        x_mm,
        y_mm,
        [
            tspan(
                f"{element_id}_line_{index}" if element_id else None,
                line,
                x_mm=x_mm,
                y_mm=y_mm + ((index - 1) * line_step_mm),
            )
            for index, line in enumerate(lines, start=1)
        ],
        style=style,
        **attrs,
    )



def wrapped_text(
    element_id: str | None,
    x_mm: float,
    y_mm: float,
    content: str,
    *,
    width_mm: float,
    line_step_mm: float | None = None,
    max_lines: int | None = None,
    overflow: str = "ellipsis",
    style: TextStyle | None = None,
    **attrs: Any,
) -> Element:
    if not isinstance(content, str):
        raise TypeError("wrapped_text() content must be a string")
    merged_attrs = merge_text_style_attrs(
        {"style": style, **attrs} if style is not None else dict(attrs),
        source="wrapped_text()",
        for_span=False,
    )
    size_pt = float(merged_attrs.get("size_pt", 12))
    letter_spacing = merged_attrs.get("letter_spacing")
    wrapped_lines = _wrap_plain_text(
        content,
        width_mm=width_mm,
        size_pt=size_pt,
        letter_spacing=None if letter_spacing is None else float(letter_spacing),
        max_lines=max_lines,
        overflow=overflow,
    )
    return multiline(
        element_id,
        x_mm,
        y_mm,
        wrapped_lines,
        line_step_mm=line_step_mm or _default_line_step_mm(size_pt),
        style=style,
        **attrs,
    )



def image(
    element_id: str | None,
    reference: str,
    x_mm: float,
    y_mm: float,
    width_mm: float,
    height_mm: float | None = None,
    **attrs: Any,
) -> Element:
    resolved_id = _element_id("image", element_id)
    clip = attrs.pop("clip", None)
    clip_id = attrs.pop("clip_id", None)
    if clip is not None:
        if isinstance(clip, Element):
            clip_def = clip_path(clip_id or f"{resolved_id}_clip", clip)
        elif isinstance(clip, DefNode):
            clip_def = clip
            if clip_def.tag != "clipPath":
                raise TypeError("image() clip DefNode must use tag='clipPath'")
            if clip_def.element_id is None:
                raise TypeError("image() clipPath defs must have an id")
        else:
            raise TypeError("image() clip must be an Element or clipPath DefNode")
        attrs["clip_def"] = clip_def
        attrs.setdefault("clip_path", f"url(#{clip_def.element_id})")

    return Element(
        kind=ElementKind.IMAGE,
        element_id=resolved_id,
        x_mm=x_mm,
        y_mm=y_mm,
        content=Asset(reference=reference, width_mm=width_mm, height_mm=height_mm),
        attrs=dict(attrs),
    )


def qr(
    element_id: str | None,
    x_mm: float,
    y_mm: float,
    data: str | bytes,
    *,
    size_mm: float,
    ecc: str = "M",
    border_modules: int = 4,
    fill: str = render_tokens.INK,
    background_fill: str | None = None,
    **attrs: Any,
) -> Element:
    if size_mm <= 0:
        raise TypeError("qr() size_mm must be positive")
    if border_modules < 0:
        raise TypeError("qr() border_modules must be zero or greater")
    if not isinstance(data, str | bytes):
        raise TypeError("qr() data must be a string or bytes")

    try:
        error_correction = _QR_ECC[ecc.upper()]
    except KeyError as exc:
        raise TypeError("qr() ecc must be one of 'L', 'M', 'Q', or 'H'") from exc

    qr_code = (
        QrCode.encode_text(data, error_correction)
        if isinstance(data, str)
        else QrCode.encode_binary(data, error_correction)
    )
    qr_id = _element_id("qr", element_id)
    label = str(attrs.pop("label", qr_id))
    shape_rendering = attrs.pop("shape_rendering", "crispEdges")
    children: list[Element] = []
    if background_fill is not None:
        children.append(
            rect(
                f"{qr_id}_bg",
                x_mm,
                y_mm,
                size_mm,
                size_mm,
                fill=background_fill,
            )
        )
    children.append(
        path(
            f"{qr_id}_fg",
            _qr_path_data(
                qr_code,
                x_mm=x_mm,
                y_mm=y_mm,
                size_mm=size_mm,
                border_modules=border_modules,
            ),
            fill=fill,
        )
    )
    return group(qr_id, label, *children, shape_rendering=shape_rendering, **attrs)



def group(
    element_id: str | None,
    label: str,
    *children: Element,
    **attrs: Any,
) -> Element:
    return Element(
        kind=ElementKind.GROUP,
        element_id=_element_id("group", element_id),
        attrs={"label": label, **attrs},
        children=_coerce_elements(_coerce_variadic_children(children), source="group()"),
    )


def path(element_id: str | None, d: str | PathBuilder, **attrs: Any) -> Element:
    return Element(
        kind=ElementKind.PATH,
        element_id=_element_id("path", element_id),
        content=d.build() if isinstance(d, PathBuilder) else d,
        attrs=dict(attrs),
    )


def line(
    element_id: str | None,
    x1_mm: float,
    y1_mm: float,
    x2_mm: float,
    y2_mm: float,
    **attrs: Any,
) -> Element:
    return Element(
        kind=ElementKind.LINE,
        element_id=_element_id("line", element_id),
        x_mm=x1_mm,
        y_mm=y1_mm,
        content=(x2_mm, y2_mm),
        attrs=dict(attrs),
    )



def rule(
    element_id: str | None,
    x_mm: float,
    y_mm: float,
    width_mm: float,
    *,
    height_mm: float = 0.3,
    fill: str,
    opacity: float | None = None,
    **attrs: Any,
) -> Element:
    return rect(
        element_id,
        x_mm,
        y_mm,
        width_mm,
        height_mm,
        fill=fill,
        opacity=opacity,
        **attrs,
    )



def svg_node(
    tag: str,
    element_id: str | None = None,
    *children: DefNode | Element,
    content: str | Markup | None = None,
    **attrs: Any,
) -> DefNode:
    return DefNode(
        tag=tag,
        element_id=_element_id(tag.replace(":", "_").replace("-", "_"), element_id),
        attrs=dict(attrs),
        children=_coerce_def_children(_coerce_variadic_children(children)),
        content=content,
    )


def markup(content: str) -> Markup:
    if not isinstance(content, str):
        raise TypeError("markup() content must be a string")
    return Markup(value=content)


def stop(element_id: str | None = None, **attrs: Any) -> DefNode:
    return svg_node("stop", element_id, **attrs)


def linear_gradient(
    element_id: str | None,
    *stops: DefNode,
    **attrs: Any,
) -> DefNode:
    return svg_node("linearGradient", element_id, *stops, **attrs)


def radial_gradient(
    element_id: str | None,
    *stops: DefNode,
    **attrs: Any,
) -> DefNode:
    return svg_node("radialGradient", element_id, *stops, **attrs)


def filter_(
    element_id: str | None,
    *children: DefNode,
    **attrs: Any,
) -> DefNode:
    return svg_node("filter", element_id, *children, **attrs)


def gaussian_blur(element_id: str | None = None, **attrs: Any) -> DefNode:
    return svg_node("feGaussianBlur", element_id, **attrs)


def offset(element_id: str | None = None, **attrs: Any) -> DefNode:
    return svg_node("feOffset", element_id, **attrs)


def component_transfer(
    element_id: str | None,
    *children: DefNode,
    **attrs: Any,
) -> DefNode:
    return svg_node("feComponentTransfer", element_id, *children, **attrs)


def func_a(element_id: str | None = None, **attrs: Any) -> DefNode:
    return svg_node("feFuncA", element_id, **attrs)


def merge(
    element_id: str | None,
    *children: DefNode,
    **attrs: Any,
) -> DefNode:
    return svg_node("feMerge", element_id, *children, **attrs)


def merge_node(element_id: str | None = None, **attrs: Any) -> DefNode:
    return svg_node("feMergeNode", element_id, **attrs)


def clip_path(
    element_id: str | None,
    *children: DefNode | Element,
    **attrs: Any,
) -> DefNode:
    return svg_node("clipPath", element_id, *children, **attrs)



def mask(
    element_id: str | None,
    *children: DefNode | Element,
    **attrs: Any,
) -> DefNode:
    return svg_node("mask", element_id, *children, **attrs)



def linear_gradient_stops(
    element_id: str | None,
    stops: Sequence[tuple[str, str] | tuple[str, str, float]],
    *,
    angle_deg: float | None = None,
    **attrs: Any,
) -> DefNode:
    gradient_attrs = dict(attrs)
    if angle_deg is not None:
        radians = math.radians(angle_deg)
        dx = math.cos(radians) * 0.5
        dy = math.sin(radians) * 0.5
        gradient_attrs.setdefault("x1", f"{0.5 - dx:.4f}".rstrip("0").rstrip("."))
        gradient_attrs.setdefault("y1", f"{0.5 - dy:.4f}".rstrip("0").rstrip("."))
        gradient_attrs.setdefault("x2", f"{0.5 + dx:.4f}".rstrip("0").rstrip("."))
        gradient_attrs.setdefault("y2", f"{0.5 + dy:.4f}".rstrip("0").rstrip("."))

    stop_nodes = []
    for index, entry in enumerate(stops, start=1):
        offset_value, color, *rest = entry
        stop_attrs: dict[str, Any] = {"offset": offset_value, "stop_color": color}
        if rest:
            stop_attrs["stop_opacity"] = rest[0]
        stop_nodes.append(stop(f"{element_id}_stop_{index}" if element_id else None, **stop_attrs))
    return linear_gradient(element_id, *stop_nodes, **gradient_attrs)



def drop_shadow(
    element_id: str | None,
    *,
    blur: float = 10,
    dx: float = 0,
    dy: float = 8,
    alpha: float = 0.75,
    **attrs: Any,
) -> DefNode:
    filter_attrs = {"x": "-20%", "y": "-20%", "width": "140%", "height": "140%", **attrs}
    shadow_id = element_id or _element_id("drop_shadow", None)
    return filter_(
        shadow_id,
        gaussian_blur(f"{shadow_id}_blur", in_="SourceAlpha", stdDeviation=str(blur)),
        offset(f"{shadow_id}_offset", dx=str(dx), dy=str(dy)),
        component_transfer(
            f"{shadow_id}_alpha",
            func_a(f"{shadow_id}_alpha_curve", type="linear", slope=str(alpha)),
        ),
        merge(
            f"{shadow_id}_merge",
            merge_node(f"{shadow_id}_merge_shadow"),
            merge_node(f"{shadow_id}_merge_graphic", in_="SourceGraphic"),
        ),
        **filter_attrs,
    )



def transform_builder() -> TransformBuilder:
    return TransformBuilder()



def path_builder() -> PathBuilder:
    return PathBuilder()



def _pt(value_mm: float) -> float:
    return round(value_mm * MM_TO_PT, 2)


def triangle(
    element_id: str | None,
    x_mm: float | None = None,
    y_mm: float | None = None,
    width_mm: float | None = None,
    height_mm: float | None = None,
    *,
    cx_mm: float | None = None,
    cy_mm: float | None = None,
    size_mm: float | None = None,
    direction: str = "right",
    **attrs: Any,
) -> Element:
    if cx_mm is not None or cy_mm is not None or size_mm is not None:
        if x_mm is not None or y_mm is not None:
            raise TypeError(
                "triangle() accepts either x_mm/y_mm or cx_mm/cy_mm positioning, not both"
            )
        if cx_mm is None or cy_mm is None or size_mm is None:
            raise TypeError(
                "triangle() center-based positioning requires cx_mm, cy_mm, and size_mm"
            )
        width_value = width_mm if width_mm is not None else size_mm
        height_value = height_mm if height_mm is not None else size_mm
        x_origin = cx_mm - (width_value / 2.0)
        y_origin = cy_mm - (height_value / 2.0)
    else:
        if x_mm is None or y_mm is None or width_mm is None or height_mm is None:
            raise TypeError(
                "triangle() requires either x_mm, y_mm, width_mm, height_mm "
                "or cx_mm, cy_mm, size_mm"
            )
        width_value = width_mm
        height_value = height_mm
        x_origin = x_mm
        y_origin = y_mm

    points_by_direction = {
        "right": (
            (x_origin, y_origin),
            (x_origin, y_origin + height_value),
            (x_origin + width_value, y_origin + (height_value / 2.0)),
        ),
        "left": (
            (x_origin + width_value, y_origin),
            (x_origin + width_value, y_origin + height_value),
            (x_origin, y_origin + (height_value / 2.0)),
        ),
        "up": (
            (x_origin, y_origin + height_value),
            (x_origin + width_value, y_origin + height_value),
            (x_origin + (width_value / 2.0), y_origin),
        ),
        "down": (
            (x_origin, y_origin),
            (x_origin + width_value, y_origin),
            (x_origin + (width_value / 2.0), y_origin + height_value),
        ),
    }
    try:
        points = points_by_direction[direction]
    except KeyError as exc:
        raise ValueError(
            f"triangle() direction must be one of {tuple(points_by_direction)}"
        ) from exc

    builder = PathBuilder().move_to(*points[0])
    for x_point, y_point in points[1:]:
        builder.line_to(x_point, y_point)
    return path(element_id, builder.close(), **attrs)


def render(*pages: Page, metadata: dict[str, Any] | None = None) -> Document:
    page_list: tuple[Page, ...]
    if len(pages) == 1 and isinstance(pages[0], Sequence) and not isinstance(pages[0], Page):
        page_list = tuple(pages[0])
    else:
        page_list = tuple(pages)
    if not all(isinstance(page, Page) for page in page_list):
        raise TypeError("render() expects Page instances")
    return Document(pages=page_list, metadata=metadata or {})
