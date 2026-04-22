from __future__ import annotations

from collections.abc import Sequence
from typing import Protocol, TypeAlias

from folio.dsl.model import Document, Page

PageSequence: TypeAlias = Sequence[Page]


class DocumentFactory(Protocol):
    def __call__(self) -> Document: ...


__all__ = ["DocumentFactory", "PageSequence"]
