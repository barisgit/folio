"""Hatch build hook that refuses to ship a stale docs index.

The hook imports the folio docs generator, produces the current index in
memory, and compares it against the committed `src/folio/docs/index.json`.
If they differ (apart from the `generated_at` timestamp), the build fails
with a message directing the developer at the regeneration command.

The hook never writes to `src/`. Regeneration is an explicit developer
action via `python -m folio.docs.generate` (or `folio docs generate`).
"""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any

from hatchling.builders.hooks.plugin.interface import BuildHookInterface

_INDEX_RELPATH = "src/folio/docs/index.json"
_IGNORED_KEYS = frozenset({"generated_at", "folio_version"})
_REGEN_COMMAND = "python -m folio.docs.generate"


class FolioDocsIndexHook(BuildHookInterface):
    """Fail the build if the committed DSL docs index is stale."""

    PLUGIN_NAME = "folio-docs-index"

    def initialize(self, version: str, build_data: dict[str, Any]) -> None:
        _ = version, build_data
        root = Path(self.root).resolve()
        committed_path = root / _INDEX_RELPATH
        if not committed_path.is_file():
            raise FileNotFoundError(
                f"committed docs index missing at {_INDEX_RELPATH}; run `{_REGEN_COMMAND}`"
            )
        committed = _strip_ignored(json.loads(committed_path.read_text(encoding="utf-8")))

        src_path = root / "src"
        sys.path.insert(0, str(src_path))
        try:
            from folio.docs.generate import build_index  # noqa: PLC0415
        finally:
            try:
                sys.path.remove(str(src_path))
            except ValueError:
                pass
        current = _strip_ignored(
            build_index(generated_at=committed.get("generated_at", "")).to_dict()
        )

        if current != committed:
            raise RuntimeError(
                "folio.docs: committed src/folio/docs/index.json is stale. "
                f"Run `{_REGEN_COMMAND}` and commit the result."
            )


def _strip_ignored(payload: dict[str, Any]) -> dict[str, Any]:
    return {key: value for key, value in payload.items() if key not in _IGNORED_KEYS}
