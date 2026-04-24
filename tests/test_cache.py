from __future__ import annotations

from pathlib import Path

from folio.core.cache import cache_paths


def test_cache_paths_are_namespaced_by_spec_file() -> None:
    folio_spec = Path("/tmp/project/config/folio.py")
    alternate_spec = Path("/tmp/project/config/custom.py")

    folio_cache = cache_paths(folio_spec)
    alternate_cache = cache_paths(alternate_spec)

    assert folio_cache.root != alternate_cache.root
    assert folio_cache.last_build.parent == folio_cache.root
    assert alternate_cache.last_build.parent == alternate_cache.root
