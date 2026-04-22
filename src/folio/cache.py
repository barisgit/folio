from __future__ import annotations

import json
import re
from dataclasses import dataclass
from datetime import UTC, datetime
from hashlib import sha256
from pathlib import Path
from typing import Any

from folio.dsl.renderer import BuildResult


@dataclass(frozen=True)
class CachePaths:
    root: Path
    last_build: Path
    reconcile: Path
    preview: Path


@dataclass(frozen=True)
class CachedPage:
    page_number: int
    filename: str
    cache_path: Path
    sha256: str


@dataclass(frozen=True)
class CachedBuildFiles:
    page_map: dict[int, Path]
    spec_snapshot: Path
    manifest: Path


class CacheError(Exception):
    """Raised when cache state is missing or invalid."""


def _spec_cache_key(spec_path: Path) -> str:
    safe_stem = re.sub(r"[^A-Za-z0-9_.-]+", "-", spec_path.stem).strip("-") or "spec"
    digest = sha256(str(spec_path.resolve()).encode("utf-8")).hexdigest()[:10]
    return f"{safe_stem}-{digest}"


def cache_paths(spec_path: Path) -> CachePaths:
    root = spec_path.parent / ".cache" / "folio" / _spec_cache_key(spec_path)
    return CachePaths(
        root=root,
        last_build=root / "last_build",
        reconcile=root / "reconcile",
        preview=root / "preview",
    )


def ensure_cache_dirs(paths: CachePaths) -> None:
    paths.last_build.mkdir(parents=True, exist_ok=True)
    paths.reconcile.mkdir(parents=True, exist_ok=True)
    paths.preview.mkdir(parents=True, exist_ok=True)


def _hash_text(content: str) -> str:
    return sha256(content.encode("utf-8")).hexdigest()


def cache_build(result: BuildResult, *, spec_path: Path) -> CachedBuildFiles:
    paths = cache_paths(spec_path)
    ensure_cache_dirs(paths)

    page_map: dict[int, Path] = {}
    for page in result.pages:
        target = paths.last_build / f"p{page.page_number}.svg"
        target.write_text(page.content, encoding="utf-8")
        page_map[page.page_number] = target

    spec_snapshot = paths.last_build / spec_path.name
    spec_snapshot.write_text(spec_path.read_text(encoding="utf-8"), encoding="utf-8")

    manifest = paths.last_build / "manifest.json"
    payload = {
        "built_at": datetime.now(tz=UTC).isoformat(),
        "spec": str(spec_path),
        "config_hash": result.config_hash,
        "pages": {
            str(page.page_number): {
                "page_id": page.page_id,
                "filename": page.filename,
                "cache_path": str(page_map[page.page_number]),
                "sha256": _hash_text(page.content),
            }
            for page in result.pages
        },
    }
    manifest.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    return CachedBuildFiles(page_map=page_map, spec_snapshot=spec_snapshot, manifest=manifest)


def _load_manifest(spec_path: Path) -> dict[str, Any]:
    resolved_spec = spec_path.resolve()
    manifest_path = cache_paths(resolved_spec).last_build / "manifest.json"
    if not manifest_path.exists():
        raise CacheError(f"Missing cache manifest: {manifest_path}")
    try:
        payload = json.loads(manifest_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise CacheError(f"Invalid cache manifest: {manifest_path}: {exc}") from exc

    if payload.get("spec") != str(resolved_spec):
        raise CacheError(
            f"Cache manifest belongs to a different spec: {manifest_path} -> {payload.get('spec')}"
        )
    return payload


def cached_pages(spec_path: Path) -> list[CachedPage]:
    payload = _load_manifest(spec_path)
    raw_pages = payload.get("pages")
    if not isinstance(raw_pages, dict):
        raise CacheError("Cache manifest is missing page data")

    pages: list[CachedPage] = []
    for raw_number, page_data in raw_pages.items():
        if not isinstance(page_data, dict):
            raise CacheError(f"Invalid cache entry for page {raw_number}")
        try:
            page_number = int(raw_number)
            filename = str(page_data["filename"])
            cache_path = Path(str(page_data["cache_path"]))
            sha_value = str(page_data["sha256"])
        except (KeyError, TypeError, ValueError) as exc:
            raise CacheError(f"Invalid cache entry for page {raw_number}") from exc
        pages.append(
            CachedPage(
                page_number=page_number, filename=filename, cache_path=cache_path, sha256=sha_value
            )
        )

    if not pages:
        raise CacheError("Cache manifest contains no pages")
    return sorted(pages, key=lambda page: page.page_number)


def last_build_svg(spec_path: Path, page_number: int) -> Path:
    path = cache_paths(spec_path).last_build / f"p{page_number}.svg"
    if not path.exists():
        raise CacheError(f"Missing cached build for page {page_number}: {path}")
    return path


def reconcile_report_path(spec_path: Path, page_number: int) -> Path:
    paths = cache_paths(spec_path)
    ensure_cache_dirs(paths)
    stamp = datetime.now(tz=UTC).isoformat().replace(":", "-")
    return paths.reconcile / f"{stamp}_p{page_number}.json"


def preview_output_path(spec_path: Path, page_number: int) -> Path:
    paths = cache_paths(spec_path)
    ensure_cache_dirs(paths)
    return paths.preview / f"p{page_number}.png"
