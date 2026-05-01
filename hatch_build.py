"""Hatch build hook for generated docs and playground assets.

The hook imports the folio docs generator, produces the current index in
memory, and compares it against the committed `src/folio/docs/index.json`.
If they differ (apart from the `generated_at` timestamp), the build fails
with a message directing the developer at the regeneration command.

The hook also runs the maintainer-only Bun playground build before checking
that the compiled assets and manifest are present. Runtime users running
`folio dev` still consume packaged static files and do not need Bun.
"""

from __future__ import annotations

import hashlib
import json
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Any

from hatchling.builders.hooks.plugin.interface import (  # type: ignore[import-untyped]  # build-time dep, not in type-check env
    BuildHookInterface,
)

_INDEX_RELPATH = "src/folio/services/docs/index.json"
_IGNORED_KEYS = frozenset({"generated_at", "folio_version"})
_REGEN_COMMAND = "python -m folio.services.docs.generate"
_PLAYGROUND_ASSET_DIR = Path("src/folio/services/playground_assets")
_PLAYGROUND_REQUIRED_ASSETS = ("index.html", "playground.js", "playground.css", "manifest.json")
_PLAYGROUND_TYPES_REGEN_COMMAND = "python -m folio._dev.gen_playground_types"
_PLAYGROUND_INSTALL_COMMAND = ("bun", "install", "--frozen-lockfile")
_PLAYGROUND_REBUILD_COMMAND = ("bun", "run", "build:playground")


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
            from folio.services.docs.generate import build_index  # noqa: PLC0415
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
                "folio.docs: committed src/folio/services/docs/index.json is stale. "
                f"Run `{_REGEN_COMMAND}` and commit the result."
            )

        _generate_playground_types(root)
        _build_playground_assets(root)
        _check_playground_assets(root)


def _strip_ignored(payload: dict[str, Any]) -> dict[str, Any]:
    return {key: value for key, value in payload.items() if key not in _IGNORED_KEYS}


def _format_command(command: tuple[str, ...]) -> str:
    return " ".join(command)


def _generate_playground_types(root: Path) -> None:
    """Regenerate ``api.generated.ts`` from Pydantic models.

    Runs in-process so wheel builds never ship a stale TS surface, even
    if a maintainer forgot to commit a regenerated file. The codegen
    helper itself lives under ``src/folio/_dev/`` and is excluded from
    both the wheel and the sdist.
    """

    src_path = root / "src"
    sys.path.insert(0, str(src_path))
    try:
        from folio._dev.gen_playground_types import main as gen_main  # noqa: PLC0415
    finally:
        try:
            sys.path.remove(str(src_path))
        except ValueError:
            pass
    if gen_main([]) != 0:
        raise RuntimeError(
            "folio playground type codegen failed. "
            f"Run `{_PLAYGROUND_TYPES_REGEN_COMMAND}` and retry."
        )


def _build_playground_assets(root: Path) -> None:
    if shutil.which(_PLAYGROUND_INSTALL_COMMAND[0]) is None:
        raise RuntimeError(
            "folio playground assets require Bun during Python package builds. "
            f"Install Bun, then run `{_format_command(_PLAYGROUND_REBUILD_COMMAND)}`."
        )

    for command in (_PLAYGROUND_INSTALL_COMMAND, _PLAYGROUND_REBUILD_COMMAND):
        try:
            subprocess.run(command, cwd=root, check=True)  # noqa: S603
        except subprocess.CalledProcessError as exc:
            raise RuntimeError(
                "folio playground asset build failed. "
                f"Run `{_format_command(command)}` from the repo root and retry."
            ) from exc


def _check_playground_assets(root: Path) -> None:
    asset_dir = root / _PLAYGROUND_ASSET_DIR
    missing = [name for name in _PLAYGROUND_REQUIRED_ASSETS if not (asset_dir / name).is_file()]
    if missing:
        joined = ", ".join(str(_PLAYGROUND_ASSET_DIR / name) for name in missing)
        raise FileNotFoundError(
            f"folio playground assets missing: {joined}. "
            f"Run `{_format_command(_PLAYGROUND_REBUILD_COMMAND)}` and commit the result."
        )

    manifest_path = asset_dir / "manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    source_hashes = manifest.get("sourceHashes")
    if not isinstance(source_hashes, dict):
        raise RuntimeError(
            "folio playground assets: manifest.json is missing sourceHashes. "
            f"Run `{_format_command(_PLAYGROUND_REBUILD_COMMAND)}` and commit the result."
        )

    stale: list[str] = []
    for relpath, expected_hash in sorted(source_hashes.items()):
        source_path = root / relpath
        if not source_path.is_file():
            stale.append(relpath)
            continue
        actual_hash = hashlib.sha256(source_path.read_bytes()).hexdigest()
        if actual_hash != expected_hash:
            stale.append(relpath)

    if stale:
        joined = ", ".join(stale)
        raise RuntimeError(
            f"folio playground assets are stale for: {joined}. "
            f"Run `{_format_command(_PLAYGROUND_REBUILD_COMMAND)}` and commit the result."
        )
