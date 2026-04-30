from __future__ import annotations

import re
import types
import warnings
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Literal

import folio.core.render.tokens as render_tokens
from folio.core.dsl.styles import TextStyle, merge_text_style_attrs
from folio.core.dsl.tweaks import TweakValue

RenderMode = Literal["build", "playground"]
"""Render mode for SVG output.

``build`` (default) emits concrete resolved primitives for every
attribute. ``playground`` emits CSS custom properties for live-safe
``TweakValue`` attributes while preserving concrete fallbacks.
"""

# Live-eligible attribute names accept ``TweakValue`` wrappers and route
# through ``_format_live_eligible_value`` instead of ``_mm``/``_pt``
# numeric normalization. Both source-side authored keys (``font_size_pt``)
# and target-side SVG names (``font-size``) are listed so the normalizer
# can match either form. Geometry attributes are intentionally absent.
_LIVE_ELIGIBLE_ATTRS: frozenset[str] = frozenset(
    {
        "fill",
        "stroke",
        "opacity",
        "fill_opacity",
        "fill-opacity",
        "stroke_opacity",
        "stroke-opacity",
        "font_size_pt",
        "font-size",
        "letter_spacing",
        "letter-spacing",
        "stroke_width_pt",
        "stroke-width",
    }
)


def _format_live_eligible_value(value: object, *, mode: RenderMode) -> object:
    """Format a value for a live-eligible attribute.

    Build mode always returns the resolved concrete primitive. Playground
    mode emits a CSS custom property reference only for live-mode tweak
    values and includes the render-time resolved value as the fallback.
    """

    if isinstance(value, TweakValue):
        resolved = value.value
        if mode == "playground" and value.mode == "live":
            return f"var({value.css_var}, {resolved})"
        return resolved
    return value


def _float_if_numeric(value: object) -> object:
    if isinstance(value, int | float):
        return float(value)
    return value


from folio.core.model import (
    Asset,
    DefNode,
    Document,
    DocumentCollection,
    Element,
    ElementKind,
    ExportFormat,
    ExportPreset,
    ExportScope,
    Markup,
    Page,
    TextSpan,
)
from folio.core.model.result import (
    BuildResult,
    RenderedDocument,
    RenderedPage,
    RenderError,
    ValidationWarning,
    config_digest,
)
from folio.core.render.primitives import (
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
from folio.core.render.primitives import (
    group as group_mm,
)
from folio.core.render.primitives import (
    tspan as tspan_mm,
)

_HEX_COLOR_RE = re.compile(r"#(?:[0-9a-fA-F]{3}|[0-9a-fA-F]{4}|[0-9a-fA-F]{6}|[0-9a-fA-F]{8})")
_LEGACY_SVG_PRESET = ExportPreset(
    name="svg",
    format=ExportFormat.SVG,
    scope=ExportScope.PAGE,
)


def _structured_defs(
    defs: str | Markup | tuple[DefNode, ...],
) -> tuple[DefNode, ...]:
    if isinstance(defs, str | Markup):
        return ()
    return defs


def _token_hex_colors() -> frozenset[str]:
    return frozenset(
        value.lower()
        for value in vars(render_tokens).values()
        if isinstance(value, str) and _HEX_COLOR_RE.fullmatch(value)
    )


def _resolve_asset(base_dir: Path, reference: str) -> Path:
    path = Path(reference)
    candidates = [path] if path.is_absolute() else [base_dir / path, Path.cwd() / path]
    for candidate in candidates:
        if candidate.exists():
            return candidate
    tried = ", ".join(str(candidate) for candidate in candidates)
    raise RenderError(f"Asset not found: {reference} -> tried {tried}")


def _coerce_collection(candidate: object, *, source: str) -> DocumentCollection:
    if isinstance(candidate, DocumentCollection):
        return candidate
    if isinstance(candidate, Document):
        warnings.warn(
            f"{source} returned a bare Document; wrap it in collection(document(...))",
            DeprecationWarning,
            stacklevel=3,
        )
        return DocumentCollection(documents=(candidate,))
    if isinstance(candidate, Sequence) and not isinstance(candidate, str | bytes):
        documents: list[Document] = []
        for item in candidate:
            if not isinstance(item, Document):
                break
            documents.append(item)
        else:
            warnings.warn(
                f"{source} returned a sequence of Document values; use collection(...) instead",
                DeprecationWarning,
                stacklevel=3,
            )
            return DocumentCollection(documents=tuple(documents))
    raise RenderError(
        f"{source} must produce a folio.dsl.DocumentCollection. Use "
        "collection(document('id', pages=[...]))."
    )


def collection_from_module(dsl_module: types.ModuleType) -> DocumentCollection:
    build = getattr(dsl_module, "build", None)
    if callable(build):
        return _coerce_collection(build(), source="module.build()")

    module_collection = getattr(dsl_module, "collection", None)
    if isinstance(module_collection, DocumentCollection):
        return module_collection

    module_document = getattr(dsl_module, "document", None)
    if isinstance(module_document, Document | DocumentCollection):
        return _coerce_collection(module_document, source="module.document")

    raise RenderError(
        "DSL module must define `def build() -> DocumentCollection` using "
        "collection(document('id', pages=[...]))."
    )


def document_from_module(dsl_module: types.ModuleType) -> Document:
    collection = collection_from_module(dsl_module)
    if len(collection.documents) != 1:
        raise RenderError(
            "document_from_module() requires exactly one document; use collection_from_module()"
        )
    return collection.documents[0]


def _text_parts(content: object, *, source: str) -> tuple[str | Markup | TextSpan, ...] | None:
    if content is None or isinstance(content, str | Markup):
        return None
    if isinstance(content, Sequence) and not isinstance(content, str | bytes):
        parts: list[str | Markup | TextSpan] = []
        for item in content:
            if not isinstance(item, str | Markup | TextSpan):
                raise RenderError(
                    f"{source} content must contain only strings, Markup, or TextSpan instances"
                )
            parts.append(item)
        return tuple(parts)
    raise RenderError(
        f"{source} content must be a string, Markup, or a sequence of strings/Markup/TextSpan"
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


def effective_export_presets(document: Document) -> tuple[ExportPreset, ...]:
    """Return declared export presets, or the legacy implicit SVG preset."""
    return document.export_presets or (_LEGACY_SVG_PRESET,)


def export_preset_map(document: Document) -> dict[str, ExportPreset]:
    presets = effective_export_presets(document)
    result: dict[str, ExportPreset] = {}
    duplicates: set[str] = set()
    for preset in presets:
        if not preset.name:
            raise RenderError("Export preset names must not be empty")
        if preset.name in result:
            duplicates.add(preset.name)
            continue
        result[preset.name] = preset
    if duplicates:
        joined = ", ".join(sorted(duplicates))
        raise RenderError(f"Duplicate export preset name: {joined}")
    return result


def export_preset_source_name(preset: ExportPreset) -> str | None:
    """Return the source preset name declared or implied by a preset."""
    if preset.format is ExportFormat.PNG:
        return preset.source or "svg"
    return preset.source


def _validate_export_preset_source(preset: ExportPreset, presets: dict[str, ExportPreset]) -> None:
    source_name = export_preset_source_name(preset)
    if source_name is None:
        return
    source = presets.get(source_name)
    if source is None:
        raise RenderError(f"Export preset {preset.name} references unknown source: {source_name}")

    if preset.format is ExportFormat.SVG:
        raise RenderError(f"SVG export preset {preset.name} cannot declare a source")
    if preset.format is ExportFormat.IDML:
        raise RenderError(f"IDML export preset {preset.name} cannot declare a source")
    if preset.format is ExportFormat.PNG:
        if source.scope is not ExportScope.PAGE or source.format is not ExportFormat.SVG:
            raise RenderError(
                f"PNG export preset {preset.name} requires a page-scoped SVG source; "
                f"{source_name} is {source.scope.value}-scoped {source.format.value}"
            )
        return
    if preset.format is ExportFormat.PDF:
        if source.scope is not ExportScope.PAGE or source.format is not ExportFormat.PNG:
            raise RenderError(
                f"PDF export preset {preset.name} requires a page-scoped PNG source; "
                f"{source_name} is {source.scope.value}-scoped {source.format.value}"
            )
        return
    raise RenderError(f"Unsupported export preset format: {preset.format}")


def _validate_export_preset_cycles(presets: dict[str, ExportPreset]) -> None:
    visiting: set[str] = set()
    visited: set[str] = set()
    path: list[str] = []

    def visit(name: str) -> None:
        if name in visited:
            return
        if name in visiting:
            start = path.index(name)
            cycle = " -> ".join([*path[start:], name])
            raise RenderError(f"Export preset dependency cycle: {cycle}")
        visiting.add(name)
        path.append(name)
        source_name = export_preset_source_name(presets[name])
        if source_name in presets:
            visit(source_name)
        path.pop()
        visiting.remove(name)
        visited.add(name)

    for name in presets:
        visit(name)


def default_export_names(document: Document) -> tuple[str, ...]:
    presets = export_preset_map(document)
    if document.default_exports is not None:
        return document.default_exports
    if "svg" in presets:
        return ("svg",)
    raise RenderError("Document default_exports is required when no svg preset exists")


def _validate_export_presets(document: Document) -> None:
    presets = export_preset_map(document)

    _validate_export_preset_cycles(presets)
    for preset in presets.values():
        _validate_export_preset_source(preset, presets)

    for name in default_export_names(document):
        if name not in presets:
            raise RenderError(f"Unknown default export preset: {name}")

    for page in document.pages:
        for name in page.extra_exports:
            preset = presets.get(name)
            if preset is None:
                raise RenderError(
                    f"Page {page.page_id or page.page_number} references unknown export preset: "
                    f"{name}"
                )
            if preset.scope is not ExportScope.PAGE:
                raise RenderError(
                    f"Page {page.page_id or page.page_number} extra_exports may only reference "
                    f"page-scoped presets: {name} is {preset.scope.value}-scoped"
                )


def resolve_export_targets(
    document: Document, requested: Sequence[str]
) -> tuple[ExportPreset, ...]:
    presets = export_preset_map(document)
    if not requested:
        names = default_export_names(document)
    elif tuple(requested) == ("all",):
        names = tuple(preset.name for preset in effective_export_presets(document))
    elif "all" in requested:
        raise RenderError("Build target 'all' cannot be combined with other targets")
    else:
        names = tuple(requested)

    resolved: list[ExportPreset] = []
    seen: set[str] = set()
    for name in names:
        preset = presets.get(name)
        if preset is None:
            raise RenderError(f"Unknown export target: {name}")
        if name in seen:
            continue
        seen.add(name)
        resolved.append(preset)
    return tuple(resolved)


def _validate_document(document: Document) -> None:
    if not document.pages:
        raise RenderError("Document defines no pages")

    _validate_export_presets(document)

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
        for node in _structured_defs(document.defs):
            _validate_def_node(node, seen_ids)
        for node in _structured_defs(page.defs):
            _validate_def_node(node, seen_ids)
        for element in page.elements:
            _validate_element(element, seen_ids)


def _hex_colors_in_attrs(attrs: Mapping[str, object]) -> set[str]:
    colors: set[str] = set()
    trusted_colors = _token_hex_colors()
    for value in attrs.values():
        candidate = _hex_string_candidate(value)
        if candidate is not None and _HEX_COLOR_RE.fullmatch(candidate):
            lowered = candidate.lower()
            if lowered not in trusted_colors:
                colors.add(lowered)
        elif isinstance(value, TextStyle) and value.fill is not None:
            fill_candidate = _hex_string_candidate(value.fill)
            if fill_candidate is None:
                continue
            lowered = fill_candidate.lower()
            if _HEX_COLOR_RE.fullmatch(lowered) and lowered not in trusted_colors:
                colors.add(lowered)
    return colors


def _hex_string_candidate(value: object) -> str | None:
    """Return ``value`` as a hex-color string when one is plausibly stored.

    Tweak helpers wrap colors in :class:`TweakValue`; they coerce to the
    resolved hex string via ``str()``. Unrelated objects return ``None``.
    """

    if isinstance(value, str):
        return value
    if isinstance(value, TweakValue):
        return str(value)
    return None


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
    for node in _structured_defs(document.defs):
        _collect_def_node_colors(node, colors)
    for page in document.pages:
        colors.update(_hex_colors_in_attrs(page.attrs))
        for node in _structured_defs(page.defs):
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


def _normalize_svg_attrs(
    attrs: dict[str, object], *, mode: RenderMode = "build"
) -> dict[str, object]:
    normalized: dict[str, object] = {}
    for key, value in attrs.items():
        if value is None:
            continue
        ends_pt = key.endswith("_pt")
        ends_mm = key.endswith("_mm")
        normalized_key = _normalize_attr_name(key[:-3] if ends_pt or ends_mm else key)
        if key in _LIVE_ELIGIBLE_ATTRS or normalized_key in _LIVE_ELIGIBLE_ATTRS:
            formatted = _format_live_eligible_value(value, mode=mode)
            # Preserve the numeric float formatting that the legacy ``_pt``
            # branch used to apply (e.g. ``font_size_pt=8`` -> ``8.0``)
            # so SVG attribute strings remain stable across the model
            # change.
            if ends_pt and isinstance(formatted, int | float):
                formatted = float(formatted)
            normalized[normalized_key] = formatted
            continue
        if (ends_mm or ends_pt) and isinstance(value, int | float | str | TweakValue):
            numeric = float(value)
            normalized[normalized_key] = m(numeric) if ends_mm else numeric
            continue
        normalized[_normalize_attr_name(key)] = value
    return normalized


def _render_text_span(span: TextSpan, *, mode: RenderMode = "build") -> str:
    attrs = merge_text_style_attrs(
        dict(span.attrs),
        source=f"TextSpan {span.element_id or '<anonymous>'}",
        for_span=True,
    )
    return tspan_mm(
        span.element_id,
        _render_text_content(span.content, mode=mode),
        raw=True,
        **_normalize_svg_attrs(attrs, mode=mode),
    )


def _render_text_content(content: object, *, mode: RenderMode = "build") -> str:
    if content is None:
        return ""
    if isinstance(content, str):
        return escape_text(content)
    if isinstance(content, Markup):
        return content.value
    parts = _text_parts(content, source="text render")
    return "".join(
        _render_text_span(part, mode=mode)
        if isinstance(part, TextSpan)
        else part.value
        if isinstance(part, Markup)
        else escape_text(part)
        for part in (parts or ())
    )


def _render_def_node(
    node: DefNode, *, config_dir: Path, mode: RenderMode = "build"
) -> str:
    attrs = _normalize_svg_attrs(dict(node.attrs), mode=mode)
    if node.element_id is not None:
        attrs = {"id": node.element_id, **attrs}
    children = []
    for child in node.children:
        if isinstance(child, DefNode):
            children.append(_render_def_node(child, config_dir=config_dir, mode=mode))
        elif isinstance(child, Element):
            children.append(_render_element(child, config_dir=config_dir, mode=mode))
        else:
            raise RenderError(f"Unsupported defs child in {node.tag}: {type(child)!r}")
    node_content = node.content.value if isinstance(node.content, Markup) else (node.content or "")
    content = node_content + "".join(children)
    attr_text = "".join(f' {key}="{value}"' for key, value in attrs.items())
    if not content:
        return f"<{node.tag}{attr_text}/>\n"
    return f"<{node.tag}{attr_text}>{content}</{node.tag}>\n"


def _defs_block(
    defs: str | Markup | tuple[DefNode, ...],
    *,
    config_dir: Path,
    mode: RenderMode = "build",
) -> str:
    if not defs:
        return ""
    if isinstance(defs, str | Markup):
        defs_text = defs.value if isinstance(defs, Markup) else defs
        return defs_text if defs_text.endswith("\n") else f"{defs_text}\n"
    content = "".join(_render_def_node(node, config_dir=config_dir, mode=mode) for node in defs)
    return f"<defs>\n{content}</defs>\n"


def _render_text(element: Element, *, mode: RenderMode = "build") -> str:
    attrs = merge_text_style_attrs(
        dict(element.attrs),
        source=f"Text element {element.element_id}",
        for_span=False,
    )
    # Route live-eligible style fields through the live-eligible formatter
    # before primitive coercion. Playground mode may return CSS variable
    # strings here, so only concrete numeric values are float-normalized.
    size_pt_raw = _format_live_eligible_value(attrs.pop("size_pt", 12), mode=mode)
    fill_raw = _format_live_eligible_value(attrs.pop("fill", "#000000"), mode=mode)
    letter_spacing_raw = attrs.pop("letter_spacing", None)
    if letter_spacing_raw is not None:
        letter_spacing_raw = _format_live_eligible_value(letter_spacing_raw, mode=mode)
    size_pt = _float_if_numeric(size_pt_raw)
    weight = int(attrs.pop("weight", 400))
    fill = str(fill_raw)
    raw = bool(attrs.pop("raw", False))
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
        content = _render_text_content(element.content, mode=mode)
    return text_mm(
        element.element_id,
        element.x_mm,
        element.y_mm,
        content,
        size_pt=size_pt,
        weight=weight,
        fill=fill,
        letter_spacing=(
            None if letter_spacing_raw is None else _float_if_numeric(letter_spacing_raw)
        ),
        anchor=anchor,
        family=None if family is None else str(family),
        italic=italic,
        font_style=None if font_style is None else str(font_style),
        raw=True,
        **_normalize_svg_attrs(attrs, mode=mode),
    )


def _render_element(
    element: Element, *, config_dir: Path, mode: RenderMode = "build"
) -> str:
    attrs = dict(element.attrs)

    if element.kind is ElementKind.RECT:
        width_mm = float(attrs.pop("width_mm"))
        height_mm = float(attrs.pop("height_mm"))
        fill = str(_format_live_eligible_value(attrs.pop("fill", "none"), mode=mode))
        return rect_mm(
            element.element_id,
            element.x_mm,
            element.y_mm,
            width_mm,
            height_mm,
            fill=fill,
            **_normalize_svg_attrs(attrs, mode=mode),
        )

    if element.kind is ElementKind.CIRCLE:
        radius_mm = float(attrs.pop("radius_mm"))
        fill = str(_format_live_eligible_value(attrs.pop("fill", "none"), mode=mode))
        return circle_mm(
            element.element_id,
            element.x_mm,
            element.y_mm,
            radius_mm,
            fill=fill,
            **_normalize_svg_attrs(attrs, mode=mode),
        )

    if element.kind is ElementKind.ELLIPSE:
        rx_mm = float(attrs.pop("rx_mm"))
        ry_mm = float(attrs.pop("ry_mm"))
        fill = str(_format_live_eligible_value(attrs.pop("fill", "none"), mode=mode))
        return ellipse_mm(
            element.element_id,
            element.x_mm,
            element.y_mm,
            rx_mm,
            ry_mm,
            fill=fill,
            **_normalize_svg_attrs(attrs, mode=mode),
        )

    if element.kind is ElementKind.TEXT:
        return _render_text(element, mode=mode)

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
            **_normalize_svg_attrs(attrs, mode=mode),
        )
        if isinstance(clip_def, DefNode):
            clip_markup = _render_def_node(clip_def, config_dir=config_dir, mode=mode)
            return f"<defs>\n{clip_markup}</defs>\n{image_markup}"
        return image_markup

    if element.kind is ElementKind.GROUP:
        label = str(attrs.pop("label", element.element_id))
        content = "".join(
            _render_element(child, config_dir=config_dir, mode=mode)
            for child in element.children
        )
        return group_mm(
            element.element_id, label, content, **_normalize_svg_attrs(attrs, mode=mode)
        )

    if element.kind is ElementKind.PATH:
        return path(
            element.element_id,
            str(element.content or ""),
            **_normalize_svg_attrs(attrs, mode=mode),
        )

    if element.kind is ElementKind.POLYGON:
        if not isinstance(element.content, tuple):
            raise RenderError(f"Polygon element {element.element_id} requires points content")
        return polygon_mm(
            element.element_id,
            element.content,
            **_normalize_svg_attrs(attrs, mode=mode),
        )

    if element.kind is ElementKind.POLYLINE:
        if not isinstance(element.content, tuple):
            raise RenderError(f"Polyline element {element.element_id} requires points content")
        return polyline_mm(
            element.element_id,
            element.content,
            **_normalize_svg_attrs(attrs, mode=mode),
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
            **_normalize_svg_attrs(attrs, mode=mode),
        )

    raise RenderError(f"Unsupported element kind for {element.element_id}: {element.kind}")


def _render_page(
    page: Page,
    *,
    config_dir: Path,
    document_defs: str | Markup | tuple[DefNode, ...] = (),
    mode: RenderMode = "build",
) -> RenderedPage:
    body = "".join(
        _render_element(element, config_dir=config_dir, mode=mode) for element in page.elements
    )
    root = group_mm(
        page.page_id,
        page.label or page.page_id,
        body,
        **{
            "data-page-number": page.page_number,
            "data-page-id": page.page_id,
            **_normalize_svg_attrs(page.attrs, mode=mode),
        },
    )
    content = (
        svg_open(page.width_mm, page.height_mm)
        + _defs_block(document_defs, config_dir=config_dir, mode=mode)
        + _defs_block(page.defs, config_dir=config_dir, mode=mode)
        + root
        + "</svg>\n"
    )
    return RenderedPage(
        page_number=page.page_number,
        page_id=page.page_id,
        filename=page.filename,
        content=content,
    )


def _render_document_pages(
    document: Document, *, config_dir: Path, mode: RenderMode = "build"
) -> list[RenderedPage]:
    validate_document(document)
    return [
        _render_page(page, config_dir=config_dir, document_defs=document.defs, mode=mode)
        for page in sorted(document.pages, key=lambda page: page.page_number)
    ]


def render_document(
    document: Document,
    *,
    config_dir: Path,
    source_path: Path | None = None,
    mode: RenderMode = "build",
) -> BuildResult:
    pages = _render_document_pages(document, config_dir=config_dir, mode=mode)
    config_hash = document.config_hash or (
        config_digest(source_path) if source_path is not None else ""
    )
    return BuildResult(
        pages=pages,
        config_hash=config_hash,
        documents=[RenderedDocument(document=document, pages=pages)],
    )


def render_collection(
    collection: DocumentCollection,
    *,
    config_dir: Path,
    source_path: Path | None = None,
    mode: RenderMode = "build",
) -> BuildResult:
    config_hash = config_digest(source_path) if source_path is not None else ""
    rendered_documents: list[RenderedDocument] = []
    pages: list[RenderedPage] = []
    for document in collection.documents:
        rendered_pages = _render_document_pages(document, config_dir=config_dir, mode=mode)
        rendered_documents.append(RenderedDocument(document=document, pages=rendered_pages))
        pages.extend(rendered_pages)
        if document.config_hash:
            config_hash = document.config_hash
    return BuildResult(pages=pages, config_hash=config_hash, documents=rendered_documents)


def build_pages(
    dsl_module: types.ModuleType,
    *,
    config_dir: Path,
    output_dir: Path | None = None,
    mode: RenderMode = "build",
) -> BuildResult:
    module_file = getattr(dsl_module, "__file__", None)
    source_path = Path(module_file).resolve() if isinstance(module_file, str) else None
    result = render_collection(
        collection_from_module(dsl_module),
        config_dir=config_dir,
        source_path=source_path,
        mode=mode,
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
