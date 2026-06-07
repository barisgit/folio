"""Entry point for regenerating `src/folio/docs/index.json`.

Run as:

    python -m folio.docs.generate

The CLI alias `folio docs generate` wires into the same `main()` function.
"""

from __future__ import annotations

import importlib.metadata
import sys
from datetime import UTC, datetime
from pathlib import Path

from folio.services.docs.discovery import DiscoveryError, discover_all
from folio.services.docs.schema import INDEX_SCHEMA_VERSION, Index
from folio.services.docs.serialize import dumps


def build_index(*, generated_at: str | None = None) -> Index:
    """Return an :class:`Index` produced by walking the public DSL surface."""
    try:
        folio_version = importlib.metadata.version("folio-dsl")
    except importlib.metadata.PackageNotFoundError:
        folio_version = "0.0.0+dev"
    timestamp = generated_at or _utcnow_iso()
    symbols = tuple(discover_all())
    return Index(
        version=INDEX_SCHEMA_VERSION,
        generated_at=timestamp,
        folio_version=folio_version,
        symbols=symbols,
    )


def index_path() -> Path:
    """Absolute path to the committed index file in this checkout."""
    return Path(__file__).resolve().parent / "index.json"


def write_index(*, destination: Path | None = None) -> Path:
    """Regenerate and overwrite the committed index. Returns the path."""
    target = destination if destination is not None else index_path()
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(dumps(build_index()), encoding="utf-8")
    return target


def main(argv: list[str] | None = None) -> int:
    _ = argv
    try:
        path = write_index()
    except DiscoveryError as exc:
        print(f"folio docs generate: {exc}", file=sys.stderr)
        return 1
    print(f"wrote {path}")
    return 0


def _utcnow_iso() -> str:
    return datetime.now(tz=UTC).strftime("%Y-%m-%dT%H:%M:%SZ")


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
