from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from folio.dsl.model import Element, Markup, TextMetrics, TextSpan


@dataclass(frozen=True, slots=True)
class TextStyle:
    font_size_pt: float | None = None
    font_weight: int | None = None
    fill: str | None = None
    fill_opacity: float | None = None
    letter_spacing: float | None = None
    text_anchor: str | None = None
    font_family: str | None = None
    font_style: str | None = None

    def text_attrs(self) -> dict[str, Any]:
        attrs: dict[str, Any] = {}
        if self.font_size_pt is not None:
            attrs["size_pt"] = self.font_size_pt
        if self.font_weight is not None:
            attrs["weight"] = self.font_weight
        if self.fill is not None:
            attrs["fill"] = self.fill
        if self.fill_opacity is not None:
            attrs["fill_opacity"] = self.fill_opacity
        if self.letter_spacing is not None:
            attrs["letter_spacing"] = self.letter_spacing
        if self.text_anchor is not None:
            attrs["anchor"] = self.text_anchor
        if self.font_family is not None:
            attrs["family"] = self.font_family
        if self.font_style is not None:
            attrs["font_style"] = self.font_style
        return attrs

    def span_attrs(self) -> dict[str, Any]:
        attrs: dict[str, Any] = {}
        if self.font_size_pt is not None:
            attrs["font_size_pt"] = self.font_size_pt
        if self.font_weight is not None:
            attrs["font_weight"] = self.font_weight
        if self.fill is not None:
            attrs["fill"] = self.fill
        if self.fill_opacity is not None:
            attrs["fill_opacity"] = self.fill_opacity
        if self.letter_spacing is not None:
            attrs["letter_spacing"] = self.letter_spacing
        if self.text_anchor is not None:
            attrs["text_anchor"] = self.text_anchor
        if self.font_family is not None:
            attrs["font_family"] = self.font_family
        if self.font_style is not None:
            attrs["font_style"] = self.font_style
        return attrs

    def __call__(
        self,
        element_id: str | None,
        x_mm: float,
        y_mm: float,
        content: str | Markup | Sequence[str | Markup | TextSpan],
        **attrs: Any,
    ) -> Element:
        from folio.dsl import text

        return text(element_id, x_mm, y_mm, content, style=self, **attrs)

    def span(
        self,
        element_id: str | None,
        content: str | Markup | Sequence[str | Markup | TextSpan],
        **attrs: Any,
    ) -> TextSpan:
        from folio.dsl import tspan

        return tspan(element_id, content, style=self, **attrs)

    def multiline(
        self,
        element_id: str | None,
        x_mm: float,
        y_mm: float,
        lines: Sequence[str | Markup | Sequence[str | Markup | TextSpan]],
        *,
        line_step_mm: float,
        **attrs: Any,
    ) -> Element:
        from folio.dsl import multiline

        return multiline(
            element_id,
            x_mm,
            y_mm,
            lines,
            line_step_mm=line_step_mm,
            style=self,
            **attrs,
        )

    def wrapped_text(
        self,
        element_id: str | None,
        x_mm: float,
        y_mm: float,
        content: str | Markup | Sequence[str | Markup | TextSpan],
        *,
        width_mm: float,
        line_step_mm: float | None = None,
        max_lines: int | None = None,
        overflow: str = "ellipsis",
        warn_on_truncate: bool = True,
        **attrs: Any,
    ) -> Element:
        from folio.dsl import wrapped_text

        return wrapped_text(
            element_id,
            x_mm,
            y_mm,
            content,
            width_mm=width_mm,
            line_step_mm=line_step_mm,
            max_lines=max_lines,
            overflow=overflow,
            warn_on_truncate=warn_on_truncate,
            style=self,
            **attrs,
        )

    def measure_text(
        self,
        content: str | Markup | Sequence[str | Markup | TextSpan],
        **attrs: Any,
    ) -> TextMetrics:
        from folio.dsl import measure_text

        return measure_text(content, style=self, **attrs)

    def measure_wrapped_text(
        self,
        content: str | Markup | Sequence[str | Markup | TextSpan],
        *,
        width_mm: float,
        line_step_mm: float | None = None,
        max_lines: int | None = None,
        overflow: str = "ellipsis",
        **attrs: Any,
    ) -> TextMetrics:
        from folio.dsl import measure_wrapped_text

        return measure_wrapped_text(
            content,
            width_mm=width_mm,
            line_step_mm=line_step_mm,
            max_lines=max_lines,
            overflow=overflow,
            style=self,
            **attrs,
        )


def coerce_text_style(style: object, *, source: str) -> TextStyle | None:
    if style is None:
        return None
    if isinstance(style, TextStyle):
        return style
    raise TypeError(f"{source} style must be a TextStyle")


def merge_text_style_attrs(
    attrs: dict[str, Any], *, source: str, for_span: bool
) -> dict[str, Any]:
    style = coerce_text_style(attrs.pop("style", None), source=source)
    merged = (style.span_attrs() if for_span else style.text_attrs()) if style else {}
    merged.update(attrs)
    return _normalize_text_attrs(merged, for_span=for_span)


def _normalize_text_attrs(attrs: dict[str, Any], *, for_span: bool) -> dict[str, Any]:
    normalized = dict(attrs)
    if for_span:
        if "size_pt" in normalized and "font_size_pt" not in normalized:
            normalized["font_size_pt"] = normalized.pop("size_pt")
        if "weight" in normalized and "font_weight" not in normalized:
            normalized["font_weight"] = normalized.pop("weight")
        if "anchor" in normalized and "text_anchor" not in normalized:
            normalized["text_anchor"] = normalized.pop("anchor")
        if "family" in normalized and "font_family" not in normalized:
            normalized["font_family"] = normalized.pop("family")
        italic = normalized.pop("italic", None)
        if italic and "font_style" not in normalized:
            normalized["font_style"] = "italic"
        return normalized

    if "font_size_pt" in normalized and "size_pt" not in normalized:
        normalized["size_pt"] = normalized.pop("font_size_pt")
    if "font_weight" in normalized and "weight" not in normalized:
        normalized["weight"] = normalized.pop("font_weight")
    if "text_anchor" in normalized and "anchor" not in normalized:
        normalized["anchor"] = normalized.pop("text_anchor")
    if "font_family" in normalized and "family" not in normalized:
        normalized["family"] = normalized.pop("font_family")
    return normalized
