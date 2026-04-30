"""Server-independent playground state and persistence helpers.

This module contains the business logic that ``folio dev`` HTTP handlers
will call. It deliberately does not start a server, open a browser, write
rendered output, or update the last-build cache.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path
from types import MappingProxyType
from typing import Any

from folio.core.dsl.tweak_values import (
    load_persisted_values,
    resolve_values_file,
    validate_persisted_values,
    write_persisted_values,
)
from folio.core.dsl.tweaks import (
    TweakDeclaration,
    TweakDiagnostic,
    TweakRegistry,
)
from folio.services.tweaks_load import load_spec_with_tweaks

__all__ = [
    "PlaygroundPage",
    "PlaygroundState",
    "PlaygroundTweak",
    "PlaygroundUpdateError",
    "apply_tweak_update",
    "load_playground_state",
]


@dataclass(frozen=True, slots=True)
class PlaygroundPage:
    """Rendered page data for playground previews."""

    page_number: int
    page_id: str
    filename: str
    svg: str


@dataclass(frozen=True, slots=True)
class PlaygroundTweak:
    """Serializable tweak declaration plus its current resolved value."""

    key: str
    group: str
    name: str
    kind: str
    mode: str
    value: Any
    default: Any
    css_var: str
    label: str | None = None
    min: float | None = None
    max: float | None = None
    options: tuple[str, ...] | None = None


@dataclass(frozen=True, slots=True)
class PlaygroundState:
    """Current playground render state.

    ``values`` is keyed by dotted tweak key and includes resolved defaults
    for declarations that are absent from ``theme.toml``.
    """

    spec_path: Path
    values_path: Path
    pages: tuple[PlaygroundPage, ...]
    tweaks: tuple[PlaygroundTweak, ...]
    values: Mapping[str, Any]
    diagnostics: tuple[TweakDiagnostic, ...]


class PlaygroundUpdateError(Exception):
    """Raised when a playground edit cannot be accepted."""

    def __init__(self, diagnostics: tuple[TweakDiagnostic, ...]) -> None:
        self.diagnostics = diagnostics
        first = next(iter(diagnostics), None)
        super().__init__(first.message if first else "playground update failed")


def load_playground_state(spec_path: Path) -> PlaygroundState:
    """Render ``spec_path`` in playground mode without touching build cache."""

    resolved_spec = spec_path.expanduser().resolve()
    outcome = load_spec_with_tweaks(resolved_spec, render_mode="playground")
    values_path = resolve_values_file(resolved_spec)
    snapshot = outcome.snapshot
    values = {
        decl.key: snapshot.values.get(decl.key, decl.default)
        for decl in snapshot.declarations
    }
    return PlaygroundState(
        spec_path=resolved_spec,
        values_path=values_path,
        pages=tuple(
            PlaygroundPage(
                page_number=page.page_number,
                page_id=page.page_id,
                filename=page.filename,
                svg=page.content,
            )
            for page in outcome.result.pages
        ),
        tweaks=tuple(
            _serialize_declaration(decl, values[decl.key])
            for decl in snapshot.declarations
        ),
        values=MappingProxyType(values),
        diagnostics=tuple(outcome.diagnostics),
    )


def apply_tweak_update(
    spec_path: Path,
    updates: Mapping[str, Any] | None = None,
    *,
    key: str | None = None,
    value: Any = None,
) -> PlaygroundState:
    """Validate and persist playground tweak edits, then return fresh state.

    Callers may pass either ``updates={"theme.brand": "#ff3366"}`` or
    ``key="theme.brand", value="#ff3366"``. The current ``theme.toml`` is
    reread immediately before validation so external edits are folded into
    the deterministic rewrite. Invalid edits raise :class:`PlaygroundUpdateError`
    and leave the values file unchanged.
    """

    normalized_updates = _normalize_updates(updates, key=key, value=value)
    resolved_spec = spec_path.expanduser().resolve()
    values_path = resolve_values_file(resolved_spec)

    # Load once to collect declarations from the current spec and to fail
    # early if the current values file is invalid. This render is cache-free.
    state = load_playground_state(resolved_spec)
    registry = _registry_from_state(state)

    unknown = tuple(
        TweakDiagnostic(
            severity="error",
            key=update_key,
            message=f"unknown tweak key {update_key!r}",
        )
        for update_key in normalized_updates
        if update_key not in registry.declarations
    )
    if unknown:
        raise PlaygroundUpdateError(unknown)

    raw = _mutable_raw(load_persisted_values(values_path))
    for update_key, update_value in normalized_updates.items():
        group, member = _split_key(update_key)
        raw.setdefault(group, {})[member] = update_value

    validated, diagnostics = validate_persisted_values(
        registry,
        raw,
        source=values_path if values_path.exists() else None,
    )
    errors = tuple(d for d in diagnostics if d.severity == "error")
    if errors:
        raise PlaygroundUpdateError(errors)

    registry.apply_values(validated)
    write_persisted_values(values_path, registry)
    return load_playground_state(resolved_spec)


def _serialize_declaration(decl: TweakDeclaration, value: Any) -> PlaygroundTweak:
    return PlaygroundTweak(
        key=decl.key,
        group=decl.group,
        name=decl.name,
        kind=decl.kind,
        mode=decl.mode,
        value=value,
        default=decl.default,
        css_var=f"--folio-tweak-{decl.key.replace('.', '-').replace('_', '-')}",
        label=decl.label,
        min=decl.min,
        max=decl.max,
        options=decl.options,
    )


def _registry_from_state(state: PlaygroundState) -> TweakRegistry:
    declarations = {
        tweak.key: TweakDeclaration(
            key=tweak.key,
            group=tweak.group,
            name=tweak.name,
            kind=tweak.kind,
            default=tweak.default,
            mode=tweak.mode,
            label=tweak.label,
            min=tweak.min,
            max=tweak.max,
            options=tweak.options,
        )
        for tweak in state.tweaks
    }
    registry = TweakRegistry(declarations=declarations)
    registry.apply_values(dict(state.values))
    return registry


def _normalize_updates(
    updates: Mapping[str, Any] | None,
    *,
    key: str | None,
    value: Any,
) -> dict[str, Any]:
    if updates is not None and key is not None:
        raise ValueError("pass either updates or key/value, not both")
    if updates is None:
        if key is None:
            raise ValueError("pass updates or key/value")
        updates = {key: value}
    normalized = dict(updates)
    if not normalized:
        raise ValueError("at least one tweak update is required")
    for update_key in normalized:
        _split_key(update_key)
    return normalized


def _split_key(key: str) -> tuple[str, str]:
    group, sep, member = key.partition(".")
    if not group or not sep or not member:
        raise ValueError(f"tweak key must be dotted as 'group.name', got {key!r}")
    return group, member


def _mutable_raw(
    raw: Mapping[str, Mapping[str, Any]] | None,
) -> dict[str, dict[str, Any]]:
    if raw is None:
        return {}
    return {group: dict(values) for group, values in raw.items()}
