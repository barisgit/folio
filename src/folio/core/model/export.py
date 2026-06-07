from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum


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
    source: str | None = None
    renderer: str | None = None
    background: str = "transparent"

    def __post_init__(self) -> None:
        object.__setattr__(self, "format", ExportFormat(self.format))
        object.__setattr__(self, "scope", ExportScope(self.scope))
