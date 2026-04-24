from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from folio.core.model.document import Element
from folio.core.model.markup import Markup


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
