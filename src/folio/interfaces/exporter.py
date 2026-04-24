"""Exporter protocol — the export subsystem contract.

Any class that can export rendered Folio documents to file formats
(PDF, IDML, PNG, etc.) satisfies this protocol via structural subtyping.
"""

from __future__ import annotations

from pathlib import Path
from typing import Protocol, runtime_checkable

from folio.core.model import RenderedDocument


@runtime_checkable
class Exporter(Protocol):
    """Exports rendered Folio documents to artifact files.

    The exporter takes rendered SVG pages and produces output files
    in formats like PDF, IDML, PNG, etc.
    """

    def execute_export_plan(
        self,
        rendered_document: RenderedDocument,
        plan: object,  # ExportPlan — avoid circular import
        out_dir: Path,
    ) -> list[Path]:
        """Execute an export plan, writing artifacts to out_dir.

        Args:
            rendered_document: The rendered document with SVG pages.
            plan: The export plan describing what to produce.
            out_dir: Directory to write output files.

        Returns:
            List of paths to written artifact files.
        """
        ...
