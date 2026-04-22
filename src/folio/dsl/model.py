from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum, auto
from typing import Any


class ElementKind(Enum):
    RECT = auto()
    CIRCLE = auto()
    TEXT = auto()
    IMAGE = auto()
    GROUP = auto()
    PATH = auto()
    LINE = auto()


@dataclass(frozen=True)
class Asset:
    reference: str
    width_mm: float
    height_mm: float | None = None


@dataclass(frozen=True)
class Markup:
    value: str


@dataclass(frozen=True)
class TextSpan:
    element_id: str | None = None
    content: str | Markup | tuple[str | Markup | TextSpan, ...] = ""
    attrs: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class Element:
    kind: ElementKind
    element_id: str
    x_mm: float = 0.0
    y_mm: float = 0.0
    content: Any = None
    attrs: dict[str, Any] = field(default_factory=dict)
    children: tuple[Element, ...] = field(default_factory=tuple)


@dataclass(frozen=True)
class DefNode:
    tag: str
    element_id: str | None = None
    attrs: dict[str, Any] = field(default_factory=dict)
    children: tuple[DefNode | Element, ...] = field(default_factory=tuple)
    content: str | Markup | None = None


@dataclass(frozen=True)
class Page:
    page_number: int
    page_id: str
    filename: str
    elements: tuple[Element, ...]
    defs: str | Markup | tuple[DefNode, ...] = field(default_factory=tuple)
    label: str | None = None
    attrs: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class Document:
    pages: tuple[Page, ...]
    config_hash: str = ""
    metadata: dict[str, Any] = field(default_factory=dict)
