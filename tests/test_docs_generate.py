from __future__ import annotations

import json
from pathlib import Path

import pytest

from folio.services.docs import VALID_KINDS
from folio.services.docs.discovery import discover_all
from folio.services.docs.generate import build_index, index_path
from folio.services.docs.schema import INDEX_SCHEMA_VERSION
from folio.services.docs.serialize import dumps


def test_index_schema_version_is_one() -> None:
    assert INDEX_SCHEMA_VERSION == 1


def test_generated_index_is_deterministic_apart_from_timestamp() -> None:
    first = build_index(generated_at="2026-04-23T00:00:00Z")
    second = build_index(generated_at="2026-04-23T00:00:00Z")
    assert dumps(first) == dumps(second)


def test_symbols_sorted_by_id() -> None:
    ids = [symbol.id for symbol in discover_all()]
    assert ids == sorted(ids)


def test_every_symbol_has_a_valid_kind() -> None:
    for symbol in discover_all():
        assert symbol.kind in VALID_KINDS, (
            f"symbol {symbol.id} has kind {symbol.kind!r} not in {VALID_KINDS}"
        )


def test_every_symbol_has_summary_and_source() -> None:
    for symbol in discover_all():
        assert symbol.summary, f"{symbol.id} missing summary"
        assert ":" in symbol.source, f"{symbol.id} has malformed source {symbol.source!r}"


def test_covers_dsl_all_tokens_and_styles() -> None:
    import folio.core.dsl.tokens as tokens
    import folio.dsl as dsl

    ids = {symbol.id for symbol in discover_all()}
    for name in dsl.__all__:
        assert f"folio.dsl.{name}" in ids, f"missing folio.dsl.{name}"
    for name in tokens.__all__:
        if name in {"STYLES", "TextStyle"}:
            continue
        assert f"folio.dsl.tokens.{name}" in ids, f"missing folio.dsl.tokens.{name}"
    for name in vars(tokens.STYLES):
        if name.startswith("_"):
            continue
        assert f"folio.dsl.tokens.STYLES.{name}" in ids, f"missing folio.dsl.tokens.STYLES.{name}"


def test_committed_index_matches_current_generator() -> None:
    committed = json.loads(index_path().read_text(encoding="utf-8"))
    current = build_index(generated_at=committed["generated_at"]).to_dict()
    stripped_committed = {k: v for k, v in committed.items() if k != "folio_version"}
    stripped_current = {k: v for k, v in current.items() if k != "folio_version"}
    assert stripped_committed == stripped_current, (
        "committed src/folio/services/docs/index.json is stale"
        " — run `python -m folio.services.docs`"
    )


def test_source_format_is_module_colon_line() -> None:
    for symbol in discover_all():
        module, _, lineno = symbol.source.partition(":")
        assert module, f"{symbol.id} source has empty module"
        assert lineno.isdigit(), f"{symbol.id} source lineno is not numeric: {symbol.source}"


def test_missing_docstring_fails_generation(monkeypatch: pytest.MonkeyPatch) -> None:
    from folio.services.docs import discovery

    class _Stub:
        __doc__ = None
        __module__ = "folio.dsl.builtins"

    def _stub_rect(*args: object, **kwargs: object) -> object:
        _ = args, kwargs
        return None

    _stub_rect.__doc__ = None  # type: ignore[attr-defined]

    import folio.dsl

    monkeypatch.setattr(folio.dsl, "rect", _stub_rect, raising=True)

    with pytest.raises(discovery.DiscoveryError, match="no docstring"):
        discover_all()


def test_index_path_points_inside_package() -> None:
    path = index_path()
    assert path.name == "index.json"
    assert path.parent.name == "docs"
    assert "folio" in path.parts


def test_committed_index_parses_and_has_symbols() -> None:
    committed = json.loads(Path(index_path()).read_text(encoding="utf-8"))
    assert committed["version"] == INDEX_SCHEMA_VERSION
    assert isinstance(committed["symbols"], list)
    assert committed["symbols"], "committed index has no symbols"
