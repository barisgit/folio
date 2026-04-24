"""Renderer protocol — the render pipeline contract.

Any class that can render a Folio document into SVG pages satisfies this
protocol via structural subtyping. No explicit inheritance required.
"""

from __future__ import annotations

from pathlib import Path
from typing import Protocol, runtime_checkable

from folio.core.model import BuildResult, Document


@runtime_checkable
class Renderer(Protocol):
    """Renders Folio documents and collections into SVG page content.

    The renderer converts the in-memory document model (Element trees)
    into SVG strings, one per page.
    """

    def render_document(
        self,
        document: Document,
        *,
        config_dir: Path,
        source_path: Path | None = None,
    ) -> BuildResult:
        """Render a single document to SVG pages.

        Args:
            document: The document to render.
            config_dir: Project directory for resolving asset paths.
            source_path: Optional spec file for config hashing.

        Returns:
            BuildResult with rendered SVG content for each page.
        """
        ...

    def validate_document(self, document: Document) -> Document:
        """Validate a document's structure without rendering.

        Returns the document unchanged if valid, raises on errors.
        """
        ...
