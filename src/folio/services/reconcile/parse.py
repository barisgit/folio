from __future__ import annotations

import re
from dataclasses import dataclass, field
from html.parser import HTMLParser
from pathlib import Path


def _strip_namespace(tag: str) -> str:
    return tag.rsplit("}", 1)[-1].rsplit(":", 1)[-1]


def _normalize_whitespace(value: str) -> str:
    return re.sub(r"\s+", " ", value).strip()


def _normalize_transform(value: str) -> str:
    return _normalize_whitespace(value.replace(",", " "))


@dataclass(frozen=True)
class ParsedElement:
    element_id: str
    tag: str
    text: str | None
    attrs: dict[str, str]
    parent_id: str | None


@dataclass(frozen=True)
class ParsedSvg:
    path: Path
    page_number: int | None
    elements: dict[str, ParsedElement]


@dataclass
class _SvgNode:
    tag: str
    attrs: dict[str, str]
    content: list[str | _SvgNode] = field(default_factory=list)

    @property
    def children(self) -> list[_SvgNode]:
        return [part for part in self.content if isinstance(part, _SvgNode)]


class _SvgTreeParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.root: _SvgNode | None = None
        self._stack: list[_SvgNode] = []

    def _node(self, tag: str, attrs: list[tuple[str, str | None]]) -> _SvgNode:
        return _SvgNode(tag=tag, attrs={key: value or "" for key, value in attrs})

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        node = self._node(tag, attrs)
        if self._stack:
            self._stack[-1].content.append(node)
        elif self.root is None:
            self.root = node
        self._stack.append(node)

    def handle_startendtag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        node = self._node(tag, attrs)
        if self._stack:
            self._stack[-1].content.append(node)
        elif self.root is None:
            self.root = node

    def handle_endtag(self, tag: str) -> None:
        stripped = _strip_namespace(tag)
        while self._stack:
            node = self._stack.pop()
            if _strip_namespace(node.tag) == stripped:
                break

    def handle_data(self, data: str) -> None:
        if self._stack:
            self._stack[-1].content.append(data)


def _itertext(node: _SvgNode) -> list[str]:
    parts: list[str] = []
    for part in node.content:
        if isinstance(part, str):
            parts.append(part)
        else:
            parts.extend(_itertext(part))
    return parts


def _is_line_tspan(node: _SvgNode) -> bool:
    attrs = {_strip_namespace(key) for key in node.attrs}
    return bool({"x", "y", "dy"} & attrs)


def _text_value(node: _SvgNode) -> str | None:
    if _strip_namespace(node.tag) not in {"text", "tspan"}:
        return None

    tspans = [child for child in node.children if _strip_namespace(child.tag) == "tspan"]
    has_inline_text = any(
        isinstance(part, str) and _normalize_whitespace(part) for part in node.content
    )
    if tspans and not has_inline_text and all(_is_line_tspan(child) for child in tspans):
        value = "\n".join(_normalize_whitespace("".join(_itertext(child))) for child in tspans)
    else:
        value = _normalize_whitespace("".join(_itertext(node)))
    return value or None


def _attrs_value(node: _SvgNode) -> dict[str, str]:
    attrs: dict[str, str] = {}
    for raw_key, raw_value in node.attrs.items():
        key = _strip_namespace(raw_key)
        value = (
            _normalize_transform(raw_value)
            if key == "transform"
            else _normalize_whitespace(raw_value)
        )
        attrs[key] = value
    return attrs


def _walk(
    node: _SvgNode, elements: dict[str, ParsedElement], current_parent_id: str | None = None
) -> None:
    element_id = node.attrs.get("id")
    next_parent_id = current_parent_id
    if element_id:
        elements[element_id] = ParsedElement(
            element_id=element_id,
            tag=_strip_namespace(node.tag),
            text=_text_value(node),
            attrs=_attrs_value(node),
            parent_id=current_parent_id,
        )
        next_parent_id = element_id

    for child in node.children:
        _walk(child, elements, next_parent_id)


def _page_number_from_attrs(elements: dict[str, ParsedElement]) -> int | None:
    for element in elements.values():
        if element.tag != "g" or element.parent_id is not None:
            continue
        raw_value = element.attrs.get("data-page-number")
        if raw_value is None:
            continue
        try:
            return int(raw_value)
        except ValueError:
            continue

    for element in elements.values():
        raw_value = element.attrs.get("data-page-number")
        if raw_value is None:
            continue
        try:
            return int(raw_value)
        except ValueError:
            continue
    return None


def detect_page_number(svg_path: Path, elements: dict[str, ParsedElement]) -> int | None:
    explicit = _page_number_from_attrs(elements)
    if explicit is not None:
        return explicit

    stem = svg_path.stem.lower()
    match = re.search(r"(?:^|[^a-z0-9])(?:page|p)(\d+)(?:[^a-z0-9]|$)", stem)
    if match:
        return int(match.group(1))
    return None


def parse_svg(svg_path: Path) -> ParsedSvg:
    try:
        parser = _SvgTreeParser()
        parser.feed(svg_path.read_text(encoding="utf-8"))
        parser.close()
    except FileNotFoundError as exc:
        raise ParseError(f"SVG not found: {svg_path}") from exc
    except Exception as exc:
        raise ParseError(f"Invalid SVG XML: {svg_path}: {exc}") from exc

    if parser.root is None:
        raise ParseError(f"Invalid SVG XML: {svg_path}: missing root element")

    elements: dict[str, ParsedElement] = {}
    _walk(parser.root, elements)
    return ParsedSvg(
        path=svg_path, page_number=detect_page_number(svg_path, elements), elements=elements
    )


class ParseError(Exception):
    """Raised when SVG parsing fails."""
