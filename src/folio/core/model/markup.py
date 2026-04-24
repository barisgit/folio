from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


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
