"""Builder protocol — the build orchestration contract.

Any class that orchestrates the full build pipeline (load → render → export)
satisfies this protocol via structural subtyping.
"""

from __future__ import annotations

from pathlib import Path
from typing import Protocol, runtime_checkable

from folio.core.model import BuildResult


@runtime_checkable
class Builder(Protocol):
    """Orchestrates the full build pipeline: load spec → render → export.

    The builder ties together module loading, rendering, target resolution,
    export execution, and caching.
    """

    def build(
        self,
        spec_path: Path,
        *,
        out_dir: Path,
        targets: tuple[str, ...] = (),
        page_number: int | None = None,
        no_cache: bool = False,
    ) -> BuildResult:
        """Run the full build pipeline.

        Args:
            spec_path: Path to the spec file (e.g., build.py).
            out_dir: Directory for rendered output.
            targets: Export target names (empty = defaults).
            page_number: Optional single page to build.
            no_cache: Skip cache write if True.

        Returns:
            BuildResult with rendered pages and export artifacts.
        """
        ...
