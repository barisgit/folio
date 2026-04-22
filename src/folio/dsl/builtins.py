from __future__ import annotations

from collections import defaultdict
from collections.abc import Iterable, Sequence
from dataclasses import dataclass
from typing import Any

from folio.dsl.model import Asset, DefNode, Document, Element, ElementKind, Markup, Page, TextSpan
from folio.dsl.styles import TextStyle, coerce_text_style
from folio.render.tokens import MM_TO_PT

_AUTO_IDS: defaultdict[str, int] = defaultdict(int)


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


def _offset_mm_attr(attrs: dict[str, Any], key: str, delta: float) -> None:
    value = attrs.get(key)
    if value is not None:
        attrs[key] = value + delta



def _offset_xy_attrs(attrs: dict[str, Any], *, x_mm: float, y_mm: float) -> dict[str, Any]:
    adjusted = dict(attrs)
    _offset_mm_attr(adjusted, "x_mm", x_mm)
    _offset_mm_attr(adjusted, "y_mm", y_mm)
    return adjusted


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



def image(
    element_id: str | None,
    reference: str,
    x_mm: float,
    y_mm: float,
    width_mm: float,
    height_mm: float | None = None,
    **attrs: Any,
) -> Element:
    return Element(
        kind=ElementKind.IMAGE,
        element_id=_element_id("image", element_id),
        x_mm=x_mm,
        y_mm=y_mm,
        content=Asset(reference=reference, width_mm=width_mm, height_mm=height_mm),
        attrs=dict(attrs),
    )


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


def path(element_id: str | None, d: str, **attrs: Any) -> Element:
    return Element(
        kind=ElementKind.PATH,
        element_id=_element_id("path", element_id),
        content=d,
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

    d = " ".join(
        [f"M{_pt(points[0][0])} {_pt(points[0][1])}"]
        + [f"L{_pt(x_point)} {_pt(y_point)}" for x_point, y_point in points[1:]]
        + ["Z"]
    )
    return path(element_id, d, **attrs)


def render(*pages: Page, metadata: dict[str, Any] | None = None) -> Document:
    page_list: tuple[Page, ...]
    if len(pages) == 1 and isinstance(pages[0], Sequence) and not isinstance(pages[0], Page):
        page_list = tuple(pages[0])
    else:
        page_list = tuple(pages)
    if not all(isinstance(page, Page) for page in page_list):
        raise TypeError("render() expects Page instances")
    return Document(pages=page_list, metadata=metadata or {})
