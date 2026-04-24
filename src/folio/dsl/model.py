from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum, StrEnum, auto
from typing import Any


class ElementKind(Enum):
    """Discriminator for every concrete :class:`Element` the DSL produces.

    Each renderer primitive (``rect``, ``circle``, ``text``, etc.) maps to
    exactly one ``ElementKind``. The enum is stable across releases and
    used by the reconcile and renderer layers to pick the right code path.

    Example:
        ElementKind.RECT

    Tags: model, enum
    """

    RECT = auto()
    CIRCLE = auto()
    ELLIPSE = auto()
    TEXT = auto()
    IMAGE = auto()
    GROUP = auto()
    PATH = auto()
    POLYGON = auto()
    POLYLINE = auto()
    LINE = auto()


class ExportFormat(StrEnum):
    """Supported export artifact formats."""

    SVG = "svg"
    PNG = "png"
    PDF = "pdf"
    IDML = "idml"


class ExportScope(StrEnum):
    """Whether an export produces page artifacts or one document artifact."""

    PAGE = "page"
    DOCUMENT = "document"


@dataclass(frozen=True)
class ExportPreset:
    """Named build target declared by a document."""

    name: str
    format: ExportFormat
    scope: ExportScope
    viewport: tuple[int, int] | None = None
    filename_pattern: str | None = None

    def __post_init__(self) -> None:
        object.__setattr__(self, "format", ExportFormat(self.format))
        object.__setattr__(self, "scope", ExportScope(self.scope))


@dataclass(frozen=True)
class Asset:
    """Reference to an external raster or vector asset with physical size.

    Produced by :func:`image` and embedded in an :class:`Element` of kind
    ``IMAGE``. ``reference`` is a project-relative path or URI; the
    renderer resolves it against the spec directory.

    Example:
        Asset(reference="assets/hero.png", width_mm=40, height_mm=30)

    Tags: model, asset
    """

    reference: str
    width_mm: float
    height_mm: float | None = None


@dataclass(frozen=True)
class Markup:
    """Trusted raw SVG markup wrapped so the renderer emits it verbatim.

    Use :func:`markup` to create one; it tells the text/defs pipeline that
    the content is already valid SVG and must not be escaped.

    Example:
        markup('<tspan fill="red">x</tspan>')

    Tags: model, text
    """

    value: str


@dataclass(frozen=True)
class TextSpan:
    """Nested text span within a :class:`Element` of kind ``TEXT``.

    Produced by :func:`tspan` / :func:`span` to style a run of text within
    a larger paragraph while inheriting the parent text element's position
    and baseline.

    Example:
        tspan(None, "inline", fill="#333")

    Tags: model, text
    """

    element_id: str | None = None
    content: str | Markup | tuple[str | Markup | TextSpan, ...] = ""
    attrs: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class Element:
    """Any drawable node in a :class:`Page`, tagged by :class:`ElementKind`.

    This is the canonical runtime shape of every DSL primitive
    (``rect``, ``circle``, ``text``, ``group``, ...). Children are
    ordered, and ids are stable so the reconcile layer can map SVG edits
    back to the spec.

    Example:
        rect(None, 0, 0, 10, 10)

    Tags: model, element
    """

    kind: ElementKind
    element_id: str
    x_mm: float = 0.0
    y_mm: float = 0.0
    content: Any = None
    attrs: dict[str, Any] = field(default_factory=dict)
    children: tuple[Element, ...] = field(default_factory=tuple)


@dataclass(frozen=True)
class DefNode:
    """Node in the SVG ``<defs>`` section (gradients, filters, clipPaths).

    Unlike :class:`Element`, a ``DefNode`` is positionless and lives in
    the document or page defs. Primitives like :func:`linear_gradient`,
    :func:`filter_`, :func:`clip_path`, and :func:`svg_node` produce it.

    Example:
        linear_gradient("bg", stop(None, offset="0%"), stop(None, offset="100%"))

    Tags: model, defs
    """

    tag: str
    element_id: str | None = None
    attrs: dict[str, Any] = field(default_factory=dict)
    children: tuple[DefNode | Element, ...] = field(default_factory=tuple)
    content: str | Markup | None = None


@dataclass(frozen=True)
class Page:
    """Top-level renderable page with a fixed size and ordered elements.

    Produced by :func:`page`. ``page_number`` drives the document order;
    ``page_id`` is a stable identifier used by reconcile; ``filename``
    controls the output SVG name.

    Example:
        page(rect(None, 0, 0, 10, 10), page_id="cover", filename="cover.svg", page_number=1)

    Tags: model, page
    """

    page_number: int
    page_id: str
    filename: str
    elements: tuple[Element, ...]
    width_mm: float = 210.0
    height_mm: float = 297.0
    defs: str | Markup | tuple[DefNode, ...] = field(default_factory=tuple)
    label: str | None = None
    attrs: dict[str, Any] = field(default_factory=dict)
    extra_exports: tuple[str, ...] = field(default_factory=tuple)


@dataclass(frozen=True)
class TextMetrics:
    """Measured dimensions of a text run produced by ``measure_*`` helpers.

    Returned by :func:`measure_text` and :func:`measure_wrapped_text`.
    Millimeter units throughout; ``line_step_mm`` is the vertical
    advance between lines; ``truncated`` is True when an overflow
    policy dropped content.

    Example:
        measure_text("Hello", style=tokens.STYLES.body)

    Tags: model, text, measurement
    """

    width_mm: float
    height_mm: float
    line_count: int
    line_step_mm: float
    truncated: bool = False


@dataclass(frozen=True)
class Document:
    """Root of a rendered multi-page document, produced by :func:`render`.

    Carries the ordered pages, document-level defs, and optional
    metadata passed into :func:`render`.

    Example:
        render(page(rect(None, 0, 0, 10, 10), page_id="p", filename="p.svg", page_number=1))

    Tags: model, document
    """

    pages: tuple[Page, ...]
    defs: str | Markup | tuple[DefNode, ...] = field(default_factory=tuple)
    config_hash: str = ""
    metadata: dict[str, Any] = field(default_factory=dict)
    document_id: str = "document"
    filename: str | None = None
    title: str | None = None
    export_presets: tuple[ExportPreset, ...] = field(default_factory=tuple)
    default_exports: tuple[str, ...] | None = None


@dataclass(frozen=True)
class DocumentCollection:
    """Top-level build value containing one or more logical documents.

    SVG/PNG outputs can still be page-oriented, but document-oriented formats
    such as IDML and PDF use this grouping to write one artifact per document.

    Example:
        collection(
            document(
                "brochure",
                pages=[page(page_id="p1", filename="p1.svg", page_number=1, elements=[])],
            )
        )

    Tags: model, document, collection
    """

    documents: tuple[Document, ...]
    metadata: dict[str, Any] = field(default_factory=dict)
