from __future__ import annotations

import html
import math
import re
import warnings
from collections import defaultdict
from collections.abc import Iterable, Sequence
from dataclasses import dataclass, field
from typing import Any

from folio.dsl.model import (
    Asset,
    DefNode,
    Document,
    Element,
    ElementKind,
    Markup,
    Page,
    TextMetrics,
    TextSpan,
)
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
_MARKUP_TAG_RE = re.compile(r"<[^>]+>")
_WRAP_TOKEN_RE = re.compile(r"\n|[^\S\n]+|[^\s\n]+")


class TextLayoutWarning(UserWarning):
    """Raised when a text layout helper truncates content."""


@dataclass(frozen=True, slots=True)
class _LayoutRun:
    content: str | Markup
    measure_text: str
    output_attrs: dict[str, Any]
    size_pt: float
    letter_spacing: float | None
    splittable: bool


@dataclass(frozen=True, slots=True)
class _WrapToken:
    kind: str
    content: str | Markup
    measure_text: str
    output_attrs: dict[str, Any]
    size_pt: float
    letter_spacing: float | None
    splittable: bool


@dataclass(slots=True)
class _LinePiece:
    content: str | Markup
    output_attrs: dict[str, Any]
    measure_text: str
    size_pt: float
    letter_spacing: float | None
    splittable: bool

    @property
    def width_mm(self) -> float:
        return _measure_text_mm(
            self.measure_text,
            size_pt=self.size_pt,
            letter_spacing=self.letter_spacing,
        )


@dataclass(slots=True)
class _LineBuilder:
    pieces: list[_LinePiece] = field(default_factory=list)
    width_mm: float = 0.0

    def append(self, piece: _LinePiece) -> None:
        self.pieces.append(piece)
        self.width_mm += piece.width_mm

    def pop(self) -> _LinePiece:
        piece = self.pieces.pop()
        self.width_mm -= piece.width_mm
        return piece


@dataclass(frozen=True, slots=True)
class _WrappedLayout:
    lines: tuple[str | Markup | tuple[str | Markup | TextSpan, ...], ...]
    metrics: TextMetrics



def _default_line_step_mm(size_pt: float) -> float:
    return round(size_pt * PT_TO_MM * _DEFAULT_LINE_HEIGHT, 2)



def _visible_markup_text(content: Markup) -> str:
    return html.unescape(_MARKUP_TAG_RE.sub("", content.value))



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
        ellipsis_width = _measure_text_mm(
            ELLIPSIS,
            size_pt=size_pt,
            letter_spacing=letter_spacing,
        )
        return ELLIPSIS if use_ellipsis and ellipsis_width <= width_mm else ""
    return f"{candidate}{suffix}"



def _validate_wrap_options(
    *,
    width_mm: float,
    line_step_mm: float | None,
    max_lines: int | None,
    overflow: str,
) -> None:
    if width_mm <= 0:
        raise TypeError("wrapped_text() width_mm must be positive")
    if line_step_mm is not None and line_step_mm <= 0:
        raise TypeError("wrapped_text() line_step_mm must be positive when provided")
    if max_lines is not None and max_lines <= 0:
        raise TypeError("wrapped_text() max_lines must be positive when provided")
    if overflow not in {"ellipsis", "clip"}:
        raise TypeError("wrapped_text() overflow must be 'ellipsis' or 'clip'")



def _root_measurement_attrs(
    *,
    style: TextStyle | None,
    attrs: dict[str, Any],
    source: str,
) -> dict[str, Any]:
    merged_attrs = merge_text_style_attrs(
        {"style": style, **attrs} if style is not None else dict(attrs),
        source=source,
        for_span=False,
    )
    return {
        "size_pt": float(merged_attrs.get("size_pt", 12)),
        "letter_spacing": (
            None
            if merged_attrs.get("letter_spacing") is None
            else float(merged_attrs["letter_spacing"])
        ),
    }



def _span_measurement_attrs(
    attrs: dict[str, Any],
    *,
    inherited: dict[str, Any],
    source: str,
) -> dict[str, Any]:
    merged = dict(inherited)
    overrides = merge_text_style_attrs(dict(attrs), source=source, for_span=False)
    for key in ("size_pt", "letter_spacing"):
        if key in overrides:
            merged[key] = float(overrides[key]) if key == "size_pt" else overrides[key]
    return merged



def _flatten_text_runs(
    content: str | Markup | Sequence[str | Markup | TextSpan],
    *,
    measure_attrs: dict[str, Any],
    output_attrs: dict[str, Any],
    source: str,
) -> list[_LayoutRun]:
    if isinstance(content, str):
        return [
            _LayoutRun(
                content=content,
                measure_text=content,
                output_attrs=dict(output_attrs),
                size_pt=float(measure_attrs["size_pt"]),
                letter_spacing=measure_attrs["letter_spacing"],
                splittable=True,
            )
        ]
    if isinstance(content, Markup):
        return [
            _LayoutRun(
                content=content,
                measure_text=_visible_markup_text(content),
                output_attrs=dict(output_attrs),
                size_pt=float(measure_attrs["size_pt"]),
                letter_spacing=measure_attrs["letter_spacing"],
                splittable=False,
            )
        ]
    runs: list[_LayoutRun] = []
    coerced = _coerce_text_content(content, source=source)
    parts: tuple[str | Markup | TextSpan, ...]
    if isinstance(coerced, str | Markup):
        parts = (coerced,)
    else:
        parts = coerced
    for part in parts:
        if isinstance(part, TextSpan):
            child_output_attrs = dict(output_attrs)
            child_output_attrs.update(
                merge_text_style_attrs(dict(part.attrs), source=source, for_span=True)
            )
            runs.extend(
                _flatten_text_runs(
                    part.content,
                    measure_attrs=_span_measurement_attrs(
                        part.attrs,
                        inherited=measure_attrs,
                        source=source,
                    ),
                    output_attrs=child_output_attrs,
                    source=source,
                )
            )
            continue
        runs.extend(
            _flatten_text_runs(
                part,
                measure_attrs=measure_attrs,
                output_attrs=output_attrs,
                source=source,
            )
        )
    return runs



def _tokenize_runs(runs: Sequence[_LayoutRun]) -> list[_WrapToken]:
    tokens: list[_WrapToken] = []
    for run in runs:
        if isinstance(run.content, Markup):
            if run.measure_text:
                tokens.append(
                    _WrapToken(
                        kind="word",
                        content=run.content,
                        measure_text=run.measure_text,
                        output_attrs=dict(run.output_attrs),
                        size_pt=run.size_pt,
                        letter_spacing=run.letter_spacing,
                        splittable=False,
                    )
                )
            continue
        for match in _WRAP_TOKEN_RE.finditer(run.content):
            part = match.group(0)
            if part == "\n":
                tokens.append(
                    _WrapToken(
                        kind="newline",
                        content="",
                        measure_text="",
                        output_attrs={},
                        size_pt=run.size_pt,
                        letter_spacing=run.letter_spacing,
                        splittable=False,
                    )
                )
            elif part.isspace():
                tokens.append(
                    _WrapToken(
                        kind="space",
                        content=" ",
                        measure_text=" ",
                        output_attrs={},
                        size_pt=run.size_pt,
                        letter_spacing=run.letter_spacing,
                        splittable=False,
                    )
                )
            else:
                tokens.append(
                    _WrapToken(
                        kind="word",
                        content=part,
                        measure_text=part,
                        output_attrs=dict(run.output_attrs),
                        size_pt=run.size_pt,
                        letter_spacing=run.letter_spacing,
                        splittable=True,
                    )
                )
    return tokens



def _token_width_mm(token: _WrapToken) -> float:
    return _measure_text_mm(
        token.measure_text,
        size_pt=token.size_pt,
        letter_spacing=token.letter_spacing,
    )



def _space_piece(token: _WrapToken) -> _LinePiece:
    return _LinePiece(
        content=" ",
        output_attrs={},
        measure_text=" ",
        size_pt=token.size_pt,
        letter_spacing=token.letter_spacing,
        splittable=True,
    )



def _line_piece_from_token(token: _WrapToken) -> _LinePiece:
    return _LinePiece(
        content=token.content,
        output_attrs=dict(token.output_attrs),
        measure_text=token.measure_text,
        size_pt=token.size_pt,
        letter_spacing=token.letter_spacing,
        splittable=token.splittable,
    )



def _truncate_piece_to_width(
    piece: _LinePiece,
    width_mm: float,
    *,
    use_ellipsis: bool,
) -> _LinePiece | None:
    if width_mm <= 0:
        return None
    if piece.splittable and isinstance(piece.content, str):
        truncated = _truncate_to_width(
            piece.content,
            width_mm=width_mm,
            size_pt=piece.size_pt,
            letter_spacing=piece.letter_spacing,
            use_ellipsis=use_ellipsis,
        )
        if not truncated:
            return None
        return _LinePiece(
            content=truncated,
            output_attrs=dict(piece.output_attrs),
            measure_text=truncated,
            size_pt=piece.size_pt,
            letter_spacing=piece.letter_spacing,
            splittable=True,
        )
    if piece.width_mm <= width_mm:
        return piece
    ellipsis_width = _measure_text_mm(
        ELLIPSIS,
        size_pt=piece.size_pt,
        letter_spacing=piece.letter_spacing,
    )
    if use_ellipsis and ellipsis_width <= width_mm:
        return _LinePiece(
            content=ELLIPSIS,
            output_attrs=dict(piece.output_attrs),
            measure_text=ELLIPSIS,
            size_pt=piece.size_pt,
            letter_spacing=piece.letter_spacing,
            splittable=True,
        )
    return None



def _append_token(line: _LineBuilder, token: _WrapToken, *, leading_space: bool) -> None:
    if leading_space:
        line.append(_space_piece(token))
    line.append(_line_piece_from_token(token))



def _append_ellipsis(line: _LineBuilder, *, width_mm: float, template: _LinePiece) -> None:
    ellipsis_piece = _LinePiece(
        content=ELLIPSIS,
        output_attrs=dict(template.output_attrs),
        measure_text=ELLIPSIS,
        size_pt=template.size_pt,
        letter_spacing=template.letter_spacing,
        splittable=True,
    )
    if line.width_mm + ellipsis_piece.width_mm <= width_mm:
        line.append(ellipsis_piece)
        return

    while line.pieces:
        last_piece = line.pop()
        truncated = _truncate_piece_to_width(
            last_piece,
            width_mm - line.width_mm,
            use_ellipsis=True,
        )
        if truncated is not None:
            line.append(truncated)
            return

    truncated = _truncate_piece_to_width(template, width_mm, use_ellipsis=True)
    if truncated is not None:
        line.append(truncated)



def _line_content(
    pieces: Sequence[_LinePiece],
) -> str | Markup | tuple[str | Markup | TextSpan, ...]:
    built: list[str | Markup | TextSpan] = []
    for piece in pieces:
        rendered: str | Markup | TextSpan
        if piece.output_attrs:
            rendered = TextSpan(None, piece.content, attrs=dict(piece.output_attrs))
        else:
            rendered = piece.content
        if isinstance(rendered, str) and built and isinstance(built[-1], str):
            built[-1] += rendered
        else:
            built.append(rendered)
    if not built:
        return ""
    if len(built) == 1 and isinstance(built[0], str | Markup):
        return built[0]
    return tuple(built)



def _line_height_mm(pieces: Sequence[_LinePiece], *, fallback_size_pt: float) -> float:
    size_pt = max((piece.size_pt for piece in pieces), default=fallback_size_pt)
    return round(size_pt * PT_TO_MM, 2)



def _wrap_layout(
    content: str | Markup | Sequence[str | Markup | TextSpan],
    *,
    width_mm: float,
    line_step_mm: float | None,
    max_lines: int | None,
    overflow: str,
    style: TextStyle | None,
    attrs: dict[str, Any],
    source: str,
) -> _WrappedLayout:
    _validate_wrap_options(
        width_mm=width_mm,
        line_step_mm=line_step_mm,
        max_lines=max_lines,
        overflow=overflow,
    )
    root_measure_attrs = _root_measurement_attrs(style=style, attrs=attrs, source=source)
    resolved_line_step_mm = line_step_mm or _default_line_step_mm(root_measure_attrs["size_pt"])
    runs = _flatten_text_runs(
        _coerce_text_content(content, source=source),
        measure_attrs=root_measure_attrs,
        output_attrs={},
        source=source,
    )
    tokens = _tokenize_runs(runs)

    line = _LineBuilder()
    lines: list[_LineBuilder] = []
    pending_space = False
    truncated = False
    index = 0

    while index < len(tokens):
        token = tokens[index]
        is_last_allowed_line = max_lines is not None and len(lines) == max_lines - 1

        if token.kind == "newline":
            if is_last_allowed_line and index < len(tokens) - 1:
                truncated = True
                if overflow == "ellipsis":
                    _append_ellipsis(
                        line,
                        width_mm=width_mm,
                        template=_LinePiece(
                            content=ELLIPSIS,
                            output_attrs={},
                            measure_text=ELLIPSIS,
                            size_pt=root_measure_attrs["size_pt"],
                            letter_spacing=root_measure_attrs["letter_spacing"],
                            splittable=True,
                        ),
                    )
                lines.append(line)
                break
            lines.append(line)
            line = _LineBuilder()
            pending_space = False
            index += 1
            continue

        if token.kind == "space":
            pending_space = pending_space or bool(line.pieces)
            index += 1
            continue

        token_width_mm = _token_width_mm(token)
        leading_space = pending_space and bool(line.pieces)
        required_width_mm = token_width_mm + (
            _space_piece(token).width_mm if leading_space else 0.0
        )

        if line.width_mm + required_width_mm <= width_mm:
            _append_token(line, token, leading_space=leading_space)
            pending_space = False
            index += 1
            continue

        if is_last_allowed_line:
            truncated = True
            if overflow == "ellipsis":
                _append_ellipsis(
                    line,
                    width_mm=width_mm,
                    template=_line_piece_from_token(token),
                )
            lines.append(line)
            break

        if not line.pieces:
            clipped_piece = _truncate_piece_to_width(
                _line_piece_from_token(token),
                width_mm,
                use_ellipsis=False,
            ) or _line_piece_from_token(token)
            line.append(clipped_piece)
            lines.append(line)
            line = _LineBuilder()
            pending_space = False
            index += 1
            continue

        lines.append(line)
        line = _LineBuilder()
        pending_space = False

    if not tokens:
        lines.append(line)
    elif not truncated:
        lines.append(line)

    line_contents = tuple(_line_content(item.pieces) for item in lines)
    line_count = len(lines)
    if line_count == 0:
        line_count = 1
        line_contents = ("",)
    first_line_height_mm = _line_height_mm(
        lines[0].pieces if lines else (),
        fallback_size_pt=root_measure_attrs["size_pt"],
    )
    height_mm = round(
        first_line_height_mm + (max(0, line_count - 1) * resolved_line_step_mm),
        2,
    )
    return _WrappedLayout(
        lines=line_contents,
        metrics=TextMetrics(
            width_mm=round(max((item.width_mm for item in lines), default=0.0), 2),
            height_mm=height_mm,
            line_count=line_count,
            line_step_mm=resolved_line_step_mm,
            truncated=truncated,
        ),
    )



def measure_text(
    content: str | Markup | Sequence[str | Markup | TextSpan],
    *,
    style: TextStyle | None = None,
    **attrs: Any,
) -> TextMetrics:
    root_measure_attrs = _root_measurement_attrs(style=style, attrs=attrs, source="measure_text()")
    runs = _flatten_text_runs(
        _coerce_text_content(content, source="measure_text()"),
        measure_attrs=root_measure_attrs,
        output_attrs={},
        source="measure_text()",
    )
    width_mm = round(
        sum(
            _measure_text_mm(
                run.measure_text,
                size_pt=run.size_pt,
                letter_spacing=run.letter_spacing,
            )
            for run in runs
        ),
        2,
    )
    line_step_mm = _default_line_step_mm(root_measure_attrs["size_pt"])
    return TextMetrics(
        width_mm=width_mm,
        height_mm=round(root_measure_attrs["size_pt"] * PT_TO_MM, 2),
        line_count=1,
        line_step_mm=line_step_mm,
        truncated=False,
    )



def measure_wrapped_text(
    content: str | Markup | Sequence[str | Markup | TextSpan],
    *,
    width_mm: float,
    line_step_mm: float | None = None,
    max_lines: int | None = None,
    overflow: str = "ellipsis",
    style: TextStyle | None = None,
    **attrs: Any,
) -> TextMetrics:
    return _wrap_layout(
        content,
        width_mm=width_mm,
        line_step_mm=line_step_mm,
        max_lines=max_lines,
        overflow=overflow,
        style=style,
        attrs=attrs,
        source="wrapped_text()",
    ).metrics


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
        # Only rx/ry and destination x/y are in mm-space and need pt
        # conversion. The rotation is in degrees, and the flags are
        # unit-less booleans (0 or 1); neither should be scaled by
        # MM_TO_PT, so serialize them directly instead of going via
        # ``_push``.
        rx_pt = _pt(rx_mm)
        ry_pt = _pt(ry_mm)
        dst_x_pt = _pt(self.origin_x_mm + x_mm)
        dst_y_pt = _pt(self.origin_y_mm + y_mm)
        large_flag = 1 if large_arc else 0
        sweep_flag = 1 if sweep else 0
        self.commands.append(
            f"A{rx_pt} {ry_pt} {x_axis_rotation_deg:g} "
            f"{large_flag} {sweep_flag} {dst_x_pt} {dst_y_pt}"
        )
        return self

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
        content: str | Markup | Sequence[str | Markup | TextSpan],
        *,
        width_mm: float,
        line_step_mm: float | None = None,
        max_lines: int | None = None,
        overflow: str = "ellipsis",
        warn_on_truncate: bool = True,
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
            warn_on_truncate=warn_on_truncate,
            style=style,
            **attrs,
        )

    def measure_text(
        self,
        content: str | Markup | Sequence[str | Markup | TextSpan],
        *,
        style: TextStyle | None = None,
        **attrs: Any,
    ) -> TextMetrics:
        return measure_text(content, style=style, **attrs)

    def measure_wrapped_text(
        self,
        content: str | Markup | Sequence[str | Markup | TextSpan],
        *,
        width_mm: float,
        line_step_mm: float | None = None,
        max_lines: int | None = None,
        overflow: str = "ellipsis",
        style: TextStyle | None = None,
        **attrs: Any,
    ) -> TextMetrics:
        return measure_wrapped_text(
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
        padding_mm: float = 0.0,
        padding_fill: str | None = None,
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
            padding_mm=padding_mm,
            padding_fill=padding_fill,
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
    content: str | Markup | Sequence[str | Markup | TextSpan],
    *,
    width_mm: float,
    line_step_mm: float | None = None,
    max_lines: int | None = None,
    overflow: str = "ellipsis",
    warn_on_truncate: bool = True,
    style: TextStyle | None = None,
    **attrs: Any,
) -> Element:
    layout = _wrap_layout(
        content,
        width_mm=width_mm,
        line_step_mm=line_step_mm,
        max_lines=max_lines,
        overflow=overflow,
        style=style,
        attrs=attrs,
        source="wrapped_text()",
    )
    if layout.metrics.truncated and warn_on_truncate and overflow == "ellipsis":
        warnings.warn(
            f"wrapped_text() truncated content for {element_id or 'anonymous text'}",
            TextLayoutWarning,
            stacklevel=2,
        )
    return multiline(
        element_id,
        x_mm,
        y_mm,
        layout.lines,
        line_step_mm=layout.metrics.line_step_mm,
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
    padding_mm: float = 0.0,
    padding_fill: str | None = None,
    **attrs: Any,
) -> Element:
    if size_mm <= 0:
        raise TypeError("qr() size_mm must be positive")
    if padding_mm < 0:
        raise TypeError("qr() padding_mm must be zero or greater")
    if (padding_mm * 2) >= size_mm:
        raise TypeError("qr() padding_mm must leave positive space for the QR matrix")
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
    matrix_size_mm = size_mm - (padding_mm * 2)
    if padding_fill is not None:
        children.append(
            rect(
                f"{qr_id}_pad",
                x_mm,
                y_mm,
                size_mm,
                size_mm,
                fill=padding_fill,
            )
        )
    if background_fill is not None:
        children.append(
            rect(
                f"{qr_id}_bg",
                x_mm + padding_mm,
                y_mm + padding_mm,
                matrix_size_mm,
                matrix_size_mm,
                fill=background_fill,
            )
        )
    children.append(
        path(
            f"{qr_id}_fg",
            _qr_path_data(
                qr_code,
                x_mm=x_mm + padding_mm,
                y_mm=y_mm + padding_mm,
                size_mm=matrix_size_mm,
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



def grain(
    element_id: str | None,
    *,
    base_frequency: float = 0.8,
    num_octaves: int = 2,
    seed: int = 7,
    alpha: float = 0.06,
    mode: str = "soft-light",
    **attrs: Any,
) -> DefNode:
    filter_attrs = {"x": "-20%", "y": "-20%", "width": "140%", "height": "140%", **attrs}
    grain_id = element_id or _element_id("grain", None)
    return filter_(
        grain_id,
        svg_node(
            "feTurbulence",
            f"{grain_id}_noise",
            type="fractalNoise",
            baseFrequency=str(base_frequency),
            numOctaves=str(num_octaves),
            seed=str(seed),
            stitchTiles="stitch",
            result="noise",
        ),
        svg_node(
            "feColorMatrix",
            f"{grain_id}_mono",
            in_="noise",
            type="saturate",
            values="0",
            result="grain_mono",
        ),
        component_transfer(
            f"{grain_id}_alpha",
            func_a(f"{grain_id}_alpha_curve", type="linear", slope=str(alpha)),
            in_="grain_mono",
            result="grain_alpha",
        ),
        svg_node(
            "feBlend",
            f"{grain_id}_blend",
            in_="SourceGraphic",
            in2="grain_alpha",
            mode=mode,
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


def render(
    *pages: Page,
    defs: str | Markup | Sequence[DefNode] | None = None,
    metadata: dict[str, Any] | None = None,
) -> Document:
    page_list: tuple[Page, ...]
    if len(pages) == 1 and isinstance(pages[0], Sequence) and not isinstance(pages[0], Page):
        page_list = tuple(pages[0])
    else:
        page_list = tuple(pages)
    if not all(isinstance(page, Page) for page in page_list):
        raise TypeError("render() expects Page instances")
    return Document(pages=page_list, defs=_coerce_defs(defs), metadata=metadata or {})
