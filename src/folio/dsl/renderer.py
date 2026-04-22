from __future__ import annotations

import re
import types
import warnings
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from hashlib import sha256
from pathlib import Path

from folio.dsl.model import Asset, DefNode, Document, Element, ElementKind, Markup, Page, TextSpan
from folio.dsl.styles import TextStyle, merge_text_style_attrs
from folio.render import tokens as render_tokens
from folio.render.primitives import (
    circle_mm,
    ellipse_mm,
    escape_text,
    image_mm,
    line_mm,
    m,
    path,
    polygon_mm,
    polyline_mm,
    rect_mm,
    svg_open,
    text_mm,
)
from folio.render.primitives import (
    group as group_mm,
)
from folio.render.primitives import (
    tspan as tspan_mm,
)


class RenderError(Exception):
    """Raised when DSL rendering fails."""


class ValidationWarning(UserWarning):
    """Raised for non-fatal document validation issues."""


_HEX_COLOR_RE = re.compile(r"#(?:[0-9a-fA-F]{3}|[0-9a-fA-F]{4}|[0-9a-fA-F]{6}|[0-9a-fA-F]{8})")


def _token_hex_colors() -> frozenset[str]:
    return frozenset(
        value.lower()
        for value in vars(render_tokens).values()
        if isinstance(value, str) and _HEX_COLOR_RE.fullmatch(value)
    )


@dataclass(frozen=True)
class RenderedPage:
    page_number: int
    page_id: str
    filename: str
    content: str


@dataclass(frozen=True)
class BuildResult:
    pages: list[RenderedPage]
    config_hash: str


def config_digest(source_path: Path) -> str:
    return sha256(source_path.read_bytes()).hexdigest()


def _resolve_asset(base_dir: Path, reference: str) -> Path:
    path = Path(reference)
    candidates = [path] if path.is_absolute() else [base_dir / path, Path.cwd() / path]
    for candidate in candidates:
        if candidate.exists():
            return candidate
    tried = ", ".join(str(candidate) for candidate in candidates)
    raise RenderError(f"Asset not found: {reference} -> tried {tried}")


def _coerce_document(candidate: object, *, source: str) -> Document:
    if isinstance(candidate, Document):
        return candidate
    if (
        isinstance(candidate, Sequence)
        and not isinstance(candidate, str | bytes)
        and all(isinstance(page, Page) for page in candidate)
    ):
        return Document(pages=tuple(candidate))
    raise RenderError(
        f"{source} must produce a folio.dsl.Document or a sequence of folio.dsl.Page values"
    )


def document_from_module(dsl_module: types.ModuleType) -> Document:
    document = getattr(dsl_module, "document", None)
    if document is not None:
        return _coerce_document(document, source="module.document")

    build = getattr(dsl_module, "build", None)
    if callable(build):
        return _coerce_document(build(), source="module.build()")

    pages = getattr(dsl_module, "pages", None)
    if pages is not None:
        return _coerce_document(pages, source="module.pages")

    raise RenderError(
        "DSL module must define `document = render(...)`, `pages = [...]`, "
        "or `def build() -> Document`."
    )


def _text_parts(content: object, *, source: str) -> tuple[str | Markup | TextSpan, ...] | None:
    if content is None or isinstance(content, str | Markup):
        return None
    if isinstance(content, Sequence) and not isinstance(content, str | bytes):
        parts = tuple(content)
        if not all(isinstance(part, str | Markup | TextSpan) for part in parts):
            raise RenderError(
                f"{source} content must contain only strings, Markup, or TextSpan instances"
            )
        return parts
    raise RenderError(
        f"{source} content must be a string, Markup, or a sequence of "
        "strings/Markup/TextSpan"
    )


def _validate_text_span(span: TextSpan, seen_ids: set[str]) -> None:
    if span.element_id is not None:
        if not span.element_id:
            raise RenderError("Text spans must not use empty ids")
        if span.element_id in seen_ids:
            raise RenderError(f"Duplicate element id: {span.element_id}")
        seen_ids.add(span.element_id)
    for part in _text_parts(span.content, source="TextSpan") or ():
        if isinstance(part, TextSpan):
            _validate_text_span(part, seen_ids)


def _validate_element(element: Element, seen_ids: set[str]) -> None:
    if not element.element_id:
        raise RenderError("Every element must have an id")
    if element.element_id in seen_ids:
        raise RenderError(f"Duplicate element id: {element.element_id}")
    seen_ids.add(element.element_id)
    if element.kind is ElementKind.TEXT:
        for part in _text_parts(element.content, source=f"Text element {element.element_id}") or ():
            if isinstance(part, TextSpan):
                _validate_text_span(part, seen_ids)
    clip_def = element.attrs.get("clip_def")
    if isinstance(clip_def, DefNode):
        _validate_def_node(clip_def, seen_ids)
    for child in element.children:
        _validate_element(child, seen_ids)


def _validate_def_node(node: DefNode, seen_ids: set[str]) -> None:
    if not node.tag:
        raise RenderError("Definition nodes must have a tag")
    if node.element_id:
        if node.element_id in seen_ids:
            raise RenderError(f"Duplicate element id: {node.element_id}")
        seen_ids.add(node.element_id)
    for child in node.children:
        if isinstance(child, DefNode):
            _validate_def_node(child, seen_ids)
            continue
        if isinstance(child, Element):
            _validate_element(child, seen_ids)
            continue
        raise RenderError(f"Unsupported defs child in {node.tag}: {type(child)!r}")


def _validate_document(document: Document) -> None:
    if not document.pages:
        raise RenderError("Document defines no pages")

    page_numbers: set[int] = set()
    page_ids: set[str] = set()
    filenames: set[str] = set()
    for page in document.pages:
        if not page.page_id:
            raise RenderError("Page id must not be empty")
        if page.page_number <= 0:
            raise RenderError(f"Invalid page number: {page.page_number}")
        if page.page_number in page_numbers:
            raise RenderError(f"Duplicate page number: {page.page_number}")
        if page.page_id in page_ids:
            raise RenderError(f"Duplicate page id: {page.page_id}")
        if not page.filename:
            raise RenderError("Page filename must not be empty")
        if page.filename in filenames:
            raise RenderError(f"Duplicate page filename: {page.filename}")
        if not page.filename.lower().endswith(".svg"):
            raise RenderError(f"Page filename must end with .svg: {page.filename}")
        if page.width_mm <= 0 or page.height_mm <= 0:
            raise RenderError(
                f"Page {page.page_id} must use positive width_mm/height_mm "
                f"(got {page.width_mm}x{page.height_mm})"
            )
        page_numbers.add(page.page_number)
        page_ids.add(page.page_id)
        filenames.add(page.filename)

        seen_ids: set[str] = {page.page_id}
        if isinstance(document.defs, tuple):
            for node in document.defs:
                _validate_def_node(node, seen_ids)
        if isinstance(page.defs, tuple):
            for node in page.defs:
                _validate_def_node(node, seen_ids)
        for element in page.elements:
            _validate_element(element, seen_ids)


def _hex_colors_in_attrs(attrs: Mapping[str, object]) -> set[str]:
    colors: set[str] = set()
    trusted_colors = _token_hex_colors()
    for value in attrs.values():
        if isinstance(value, str) and _HEX_COLOR_RE.fullmatch(value):
            lowered = value.lower()
            if lowered not in trusted_colors:
                colors.add(lowered)
        elif isinstance(value, TextStyle) and value.fill is not None:
            lowered = value.fill.lower()
            if _HEX_COLOR_RE.fullmatch(lowered) and lowered not in trusted_colors:
                colors.add(lowered)
    return colors


def _collect_text_span_colors(span: TextSpan, colors: set[str]) -> None:
    colors.update(_hex_colors_in_attrs(span.attrs))
    for part in _text_parts(span.content, source="TextSpan") or ():
        if isinstance(part, TextSpan):
            _collect_text_span_colors(part, colors)


def _collect_element_colors(element: Element, colors: set[str]) -> None:
    colors.update(_hex_colors_in_attrs(element.attrs))
    if element.kind is ElementKind.TEXT:
        for part in _text_parts(element.content, source=f"Text element {element.element_id}") or ():
            if isinstance(part, TextSpan):
                _collect_text_span_colors(part, colors)
    clip_def = element.attrs.get("clip_def")
    if isinstance(clip_def, DefNode):
        _collect_def_node_colors(clip_def, colors)
    for child in element.children:
        _collect_element_colors(child, colors)


def _collect_def_node_colors(node: DefNode, colors: set[str]) -> None:
    colors.update(_hex_colors_in_attrs(node.attrs))
    for child in node.children:
        if isinstance(child, DefNode):
            _collect_def_node_colors(child, colors)
        elif isinstance(child, Element):
            _collect_element_colors(child, colors)


def _warn_on_non_token_hex_colors(document: Document) -> None:
    colors: set[str] = set()
    if isinstance(document.defs, tuple):
        for node in document.defs:
            _collect_def_node_colors(node, colors)
    for page in document.pages:
        colors.update(_hex_colors_in_attrs(page.attrs))
        if isinstance(page.defs, tuple):
            for node in page.defs:
                _collect_def_node_colors(node, colors)
        for element in page.elements:
            _collect_element_colors(element, colors)
    if colors:
        joined = ", ".join(sorted(colors))
        warnings.warn(
            "Non-token hex colors detected; prefer folio.dsl.tokens constants when "
            f"possible: {joined}",
            ValidationWarning,
            stacklevel=2,
        )


def validate_document(document: Document) -> Document:
    _validate_document(document)
    _warn_on_non_token_hex_colors(document)
    return document


def _normalize_attr_name(key: str) -> str:
    trimmed = key[:-1] if key.endswith("_") else key
    return trimmed.replace("__", ":").replace("_", "-")


def _normalize_svg_attrs(attrs: dict[str, object]) -> dict[str, object]:
    normalized: dict[str, object] = {}
    for key, value in attrs.items():
        if value is None:
            continue
        if key.endswith("_mm"):
            normalized[_normalize_attr_name(key[:-3])] = m(float(value))
            continue
        if key.endswith("_pt"):
            normalized[_normalize_attr_name(key[:-3])] = float(value)
            continue
        normalized[_normalize_attr_name(key)] = value
    return normalized


def _render_text_span(span: TextSpan) -> str:
    attrs = merge_text_style_attrs(
        dict(span.attrs),
        source=f"TextSpan {span.element_id or '<anonymous>'}",
        for_span=True,
    )
    return tspan_mm(
        span.element_id,
        _render_text_content(span.content),
        raw=True,
        **_normalize_svg_attrs(attrs),
    )


def _render_text_content(content: object) -> str:
    if content is None:
        return ""
    if isinstance(content, str):
        return escape_text(content)
    if isinstance(content, Markup):
        return content.value
    parts = _text_parts(content, source="text render")
    return "".join(
        _render_text_span(part)
        if isinstance(part, TextSpan)
        else part.value
        if isinstance(part, Markup)
        else escape_text(part)
        for part in (parts or ())
    )


def _render_def_node(node: DefNode, *, config_dir: Path) -> str:
    attrs = _normalize_svg_attrs(dict(node.attrs))
    if node.element_id is not None:
        attrs = {"id": node.element_id, **attrs}
    children = []
    for child in node.children:
        if isinstance(child, DefNode):
            children.append(_render_def_node(child, config_dir=config_dir))
        elif isinstance(child, Element):
            children.append(_render_element(child, config_dir=config_dir))
        else:
            raise RenderError(f"Unsupported defs child in {node.tag}: {type(child)!r}")
    node_content = node.content.value if isinstance(node.content, Markup) else (node.content or "")
    content = node_content + "".join(children)
    attr_text = "".join(f' {key}="{value}"' for key, value in attrs.items())
    if not content:
        return f"<{node.tag}{attr_text}/>\n"
    return f"<{node.tag}{attr_text}>{content}</{node.tag}>\n"


def _defs_block(defs: str | Markup | tuple[DefNode, ...], *, config_dir: Path) -> str:
    if not defs:
        return ""
    if isinstance(defs, str | Markup):
        defs_text = defs.value if isinstance(defs, Markup) else defs
        return defs_text if defs_text.endswith("\n") else f"{defs_text}\n"
    content = "".join(_render_def_node(node, config_dir=config_dir) for node in defs)
    return f"<defs>\n{content}</defs>\n"


def _render_text(element: Element) -> str:
    attrs = merge_text_style_attrs(
        dict(element.attrs),
        source=f"Text element {element.element_id}",
        for_span=False,
    )
    size_pt = float(attrs.pop("size_pt", 12))
    weight = int(attrs.pop("weight", 400))
    fill = str(attrs.pop("fill", "#000000"))
    raw = bool(attrs.pop("raw", False))
    letter_spacing = attrs.pop("letter_spacing", None)
    anchor = str(attrs.pop("anchor", "start"))
    family = attrs.pop("family", None)
    font_style = attrs.pop("font_style", None)
    italic = bool(attrs.pop("italic", False))
    if raw:
        if not isinstance(element.content, str | Markup):
            raise RenderError(
                f"Text element {element.element_id} cannot use raw=True with structured content"
            )
        content = element.content.value if isinstance(element.content, Markup) else element.content
    else:
        content = _render_text_content(element.content)
    return text_mm(
        element.element_id,
        element.x_mm,
        element.y_mm,
        content,
        size_pt=size_pt,
        weight=weight,
        fill=fill,
        letter_spacing=None if letter_spacing is None else float(letter_spacing),
        anchor=anchor,
        family=None if family is None else str(family),
        italic=italic,
        font_style=None if font_style is None else str(font_style),
        raw=True,
        **_normalize_svg_attrs(attrs),
    )


def _render_element(element: Element, *, config_dir: Path) -> str:
    attrs = dict(element.attrs)

    if element.kind is ElementKind.RECT:
        width_mm = float(attrs.pop("width_mm"))
        height_mm = float(attrs.pop("height_mm"))
        fill = str(attrs.pop("fill", "none"))
        return rect_mm(
            element.element_id,
            element.x_mm,
            element.y_mm,
            width_mm,
            height_mm,
            fill=fill,
            **_normalize_svg_attrs(attrs),
        )

    if element.kind is ElementKind.CIRCLE:
        radius_mm = float(attrs.pop("radius_mm"))
        fill = str(attrs.pop("fill", "none"))
        return circle_mm(
            element.element_id,
            element.x_mm,
            element.y_mm,
            radius_mm,
            fill=fill,
            **_normalize_svg_attrs(attrs),
        )

    if element.kind is ElementKind.ELLIPSE:
        rx_mm = float(attrs.pop("rx_mm"))
        ry_mm = float(attrs.pop("ry_mm"))
        fill = str(attrs.pop("fill", "none"))
        return ellipse_mm(
            element.element_id,
            element.x_mm,
            element.y_mm,
            rx_mm,
            ry_mm,
            fill=fill,
            **_normalize_svg_attrs(attrs),
        )

    if element.kind is ElementKind.TEXT:
        return _render_text(element)

    if element.kind is ElementKind.IMAGE:
        if not isinstance(element.content, Asset):
            raise RenderError(f"Image element {element.element_id} is missing an Asset payload")
        clip_def = attrs.pop("clip_def", None)
        asset_path = _resolve_asset(config_dir, element.content.reference)
        image_markup = image_mm(
            element.element_id,
            asset_path,
            element.x_mm,
            element.y_mm,
            element.content.width_mm,
            element.content.height_mm,
            **_normalize_svg_attrs(attrs),
        )
        if isinstance(clip_def, DefNode):
            clip_markup = _render_def_node(clip_def, config_dir=config_dir)
            return f"<defs>\n{clip_markup}</defs>\n{image_markup}"
        return image_markup

    if element.kind is ElementKind.GROUP:
        label = str(attrs.pop("label", element.element_id))
        content = "".join(
            _render_element(child, config_dir=config_dir) for child in element.children
        )
        return group_mm(element.element_id, label, content, **_normalize_svg_attrs(attrs))

    if element.kind is ElementKind.PATH:
        return path(element.element_id, str(element.content or ""), **_normalize_svg_attrs(attrs))

    if element.kind is ElementKind.POLYGON:
        if not isinstance(element.content, tuple):
            raise RenderError(f"Polygon element {element.element_id} requires points content")
        return polygon_mm(
            element.element_id,
            element.content,
            **_normalize_svg_attrs(attrs),
        )

    if element.kind is ElementKind.POLYLINE:
        if not isinstance(element.content, tuple):
            raise RenderError(f"Polyline element {element.element_id} requires points content")
        return polyline_mm(
            element.element_id,
            element.content,
            **_normalize_svg_attrs(attrs),
        )

    if element.kind is ElementKind.LINE:
        if not isinstance(element.content, tuple) or len(element.content) != 2:
            raise RenderError(f"Line element {element.element_id} requires (x2_mm, y2_mm) content")
        x2_mm, y2_mm = element.content
        return line_mm(
            element.element_id,
            element.x_mm,
            element.y_mm,
            float(x2_mm),
            float(y2_mm),
            **_normalize_svg_attrs(attrs),
        )

    raise RenderError(f"Unsupported element kind for {element.element_id}: {element.kind}")


def _render_page(
    page: Page,
    *,
    config_dir: Path,
    document_defs: str | Markup | tuple[DefNode, ...] = (),
) -> RenderedPage:
    body = "".join(_render_element(element, config_dir=config_dir) for element in page.elements)
    root = group_mm(
        page.page_id,
        page.label or page.page_id,
        body,
        **{
            "data-page-number": page.page_number,
            "data-page-id": page.page_id,
            **_normalize_svg_attrs(page.attrs),
        },
    )
    content = (
        svg_open(page.width_mm, page.height_mm)
        + _defs_block(document_defs, config_dir=config_dir)
        + _defs_block(page.defs, config_dir=config_dir)
        + root
        + "</svg>\n"
    )
    return RenderedPage(
        page_number=page.page_number,
        page_id=page.page_id,
        filename=page.filename,
        content=content,
    )


def render_document(
    document: Document,
    *,
    config_dir: Path,
    source_path: Path | None = None,
) -> BuildResult:
    validate_document(document)
    pages = [
        _render_page(page, config_dir=config_dir, document_defs=document.defs)
        for page in sorted(document.pages, key=lambda page: page.page_number)
    ]
    config_hash = document.config_hash or (
        config_digest(source_path) if source_path is not None else ""
    )
    return BuildResult(pages=pages, config_hash=config_hash)


def build_pages(
    dsl_module: types.ModuleType,
    *,
    config_dir: Path,
    output_dir: Path | None = None,
) -> BuildResult:
    source_path = (
        Path(dsl_module.__file__).resolve() if getattr(dsl_module, "__file__", None) else None
    )
    result = render_document(
        document_from_module(dsl_module), config_dir=config_dir, source_path=source_path
    )
    if output_dir is not None:
        write_pages(result, output_dir)
    return result


def write_pages(result: BuildResult, out_dir: Path) -> list[Path]:
    out_dir.mkdir(parents=True, exist_ok=True)
    written: list[Path] = []
    for page in result.pages:
        target = out_dir / page.filename
        target.write_text(page.content, encoding="utf-8")
        written.append(target)
    return written
