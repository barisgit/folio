from __future__ import annotations

from dataclasses import dataclass, field
from hashlib import sha256
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from folio.core.model.document import Document


@dataclass(frozen=True)
class RenderedPage:
    page_number: int
    page_id: str
    filename: str
    content: str


@dataclass(frozen=True)
class RenderedDocument:
    document: Document
    pages: list[RenderedPage]


@dataclass(frozen=True)
class BuildResult:
    pages: list[RenderedPage]
    config_hash: str
    documents: list[RenderedDocument] = field(default_factory=list)


class RenderError(Exception):
    """Raised when DSL rendering fails."""


class ValidationWarning(UserWarning):
    """Raised for non-fatal document validation issues."""


def config_digest(source_path: Path) -> str:
    return sha256(source_path.read_bytes()).hexdigest()
