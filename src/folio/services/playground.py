"""Server-independent playground state and persistence helpers.

This module contains the business logic that ``folio dev`` HTTP handlers
will call. It deliberately does not start a server, open a browser, write
rendered output, or update the last-build cache.
"""

from __future__ import annotations

import math
import numbers
from collections.abc import Mapping
from pathlib import Path
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from folio.core.dsl.tweak_values import (
    load_persisted_values,
    write_persisted_raw,
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
    "Diagnostic",
    "PlaygroundPage",
    "PlaygroundState",
    "PlaygroundTweak",
    "PlaygroundUpdateError",
    "ResetTweakRequest",
    "TweakUpdateRequest",
    "apply_tweak_reset",
    "apply_tweak_update",
    "load_playground_state",
]


# Aliases map snake_case Python field names to camelCase JSON keys that the
# browser-facing playground has used since its first release. Serialization
# uses ``model_dump(mode="json", by_alias=True)`` and validation accepts
# either form via ``populate_by_name=True``.
_BASE_CONFIG = ConfigDict(populate_by_name=True, frozen=True)


class PlaygroundPage(BaseModel):
    """Rendered page data for playground previews."""

    model_config = _BASE_CONFIG

    page_number: int = Field(alias="pageNumber")
    page_id: str = Field(alias="pageId")
    filename: str
    svg: str
    # Document context: which logical document this page belongs to. Used by
    # the playground UI to group pages under a doc tree (VS Code explorer
    # pattern). ``document_label`` falls back to ``document_id`` when the
    # spec did not set a title.
    document_id: str = Field(alias="documentId")
    document_label: str = Field(alias="documentLabel")
    # Page geometry in millimetres so the preview can size each page sheet
    # to its actual aspect ratio (A4 portrait, 16:9 slide, ...).
    width_mm: float = Field(alias="widthMm")
    height_mm: float = Field(alias="heightMm")


class PlaygroundTweak(BaseModel):
    """Serializable tweak declaration plus its current resolved value."""

    model_config = _BASE_CONFIG

    key: str
    group: str
    name: str
    kind: str
    mode: str
    value: Any
    default: Any
    css_var: str = Field(alias="cssVar")
    label: str | None = None
    # ``int | float`` keeps integer inputs serialized as integers (legacy parity);
    # Pydantic would otherwise coerce 32 -> 32.0 under a plain ``float``.
    min: int | float | None = None
    max: int | float | None = None
    options: tuple[str, ...] | None = None
    # True iff the resolved value differs from the spec-code default.
    # Computed from the value pair, not from key presence in ``theme.toml``,
    # so a persisted entry that happens to match the default does not
    # falsely flag the tweak as edited.
    diverged: bool = False


class Diagnostic(BaseModel):
    """Wire-format diagnostic shared with the browser."""

    model_config = _BASE_CONFIG

    severity: str
    key: str | None = None
    message: str

    @classmethod
    def from_tweak(cls, diagnostic: TweakDiagnostic) -> Diagnostic:
        return cls(
            severity=diagnostic.severity,
            key=diagnostic.key,
            message=diagnostic.message,
        )


class PlaygroundState(BaseModel):
    """Current playground render state.

    ``values`` is keyed by dotted tweak key and includes resolved defaults
    for declarations that are absent from ``theme.toml``.
    """

    model_config = _BASE_CONFIG

    spec_path: Path = Field(alias="specPath")
    values_path: Path = Field(alias="valuesPath")
    pages: tuple[PlaygroundPage, ...]
    tweaks: tuple[PlaygroundTweak, ...]
    values: dict[str, Any]
    diagnostics: tuple[Diagnostic, ...]


class TweakUpdateRequest(BaseModel):
    """Wire-format PATCH body accepted by ``/api/tweaks``.

    Two shapes are accepted: ``{"updates": {key: value, ...}}`` for batched
    edits and ``{"key": ..., "value": ...}`` for single-key edits. The model
    normalizes both into ``updates`` so callers can ignore the difference.
    """

    model_config = ConfigDict(populate_by_name=True, extra="forbid")

    updates: dict[str, Any] | None = None
    key: str | None = None
    value: Any = None

    @model_validator(mode="after")
    def _normalize(self) -> TweakUpdateRequest:
        if self.updates is not None and self.key is not None:
            raise ValueError("pass either 'updates' or 'key'/'value', not both")
        if self.updates is None and self.key is None:
            raise ValueError(
                "expected {'updates': {...}} or {'key': ..., 'value': ...}",
            )
        if self.updates is None:
            assert self.key is not None
            object.__setattr__(self, "updates", {self.key: self.value})
            object.__setattr__(self, "key", None)
            object.__setattr__(self, "value", None)
        if not self.updates:
            raise ValueError("at least one tweak update is required")
        return self

    def as_updates(self) -> dict[str, Any]:
        assert self.updates is not None
        return dict(self.updates)


class ResetTweakRequest(BaseModel):
    """Wire-format POST body accepted by ``/api/tweaks/reset``.

    Three scopes are supported:

    - ``scope="tweak"`` with ``key``: drop a single dotted key.
    - ``scope="group"`` with ``group``: drop every key in that group.
    - ``scope="all"``: drop every persisted value.

    Resetting removes the entry from ``theme.toml`` so the spec-code
    default re-applies on the next render. If the file ends up empty it
    is unlinked rather than left as a zero-byte file.
    """

    model_config = ConfigDict(populate_by_name=True, extra="forbid")

    scope: Literal["tweak", "group", "all"]
    key: str | None = None
    group: str | None = None

    @model_validator(mode="after")
    def _validate_scope(self) -> ResetTweakRequest:
        if self.scope == "tweak":
            if not self.key:
                raise ValueError("scope='tweak' requires a 'key' field")
            if self.group is not None:
                raise ValueError("scope='tweak' must not include 'group'")
        elif self.scope == "group":
            if not self.group:
                raise ValueError("scope='group' requires a 'group' field")
            if self.key is not None:
                raise ValueError("scope='group' must not include 'key'")
        else:  # "all"
            if self.key is not None or self.group is not None:
                raise ValueError("scope='all' must not include 'key' or 'group'")
        return self


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
                page_number=rendered_page.page_number,
                page_id=rendered_page.page_id,
                filename=rendered_page.filename,
                svg=rendered_page.content,
                document_id=rendered_doc.document.document_id,
                document_label=(
                    rendered_doc.document.title
                    or rendered_doc.document.document_id
                ),
                width_mm=source_page.width_mm,
                height_mm=source_page.height_mm,
            )
            for rendered_doc in outcome.result.documents
            for rendered_page, source_page in zip(
                rendered_doc.pages, rendered_doc.document.pages, strict=True
            )
        ),
        tweaks=tuple(
            _serialize_declaration(decl, values[decl.key])
            for decl in snapshot.declarations
        ),
        values=values,
        diagnostics=tuple(Diagnostic.from_tweak(d) for d in outcome.diagnostics),
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


def apply_tweak_reset(
    spec_path: Path,
    request: ResetTweakRequest,
) -> PlaygroundState:
    """Drop persisted entries per ``request`` and return fresh state.

    The spec is reloaded so unknown keys/groups are diagnosed against
    the current declarations; the values file is rewritten with the
    surviving entries (or unlinked when nothing remains).
    """

    resolved_spec = spec_path.expanduser().resolve()
    values_path = resolve_values_file(resolved_spec)

    state = load_playground_state(resolved_spec)
    registry = _registry_from_state(state)

    raw = _mutable_raw(load_persisted_values(values_path))

    if request.scope == "tweak":
        assert request.key is not None
        if request.key not in registry.declarations:
            raise PlaygroundUpdateError(
                (
                    TweakDiagnostic(
                        severity="error",
                        key=request.key,
                        message=f"unknown tweak key {request.key!r}",
                    ),
                )
            )
        group, member = _split_key(request.key)
        members = raw.get(group)
        if members is not None and member in members:
            del members[member]
            if not members:
                del raw[group]
    elif request.scope == "group":
        assert request.group is not None
        known_groups = {decl.group for decl in registry.declarations.values()}
        if request.group not in known_groups:
            raise PlaygroundUpdateError(
                (
                    TweakDiagnostic(
                        severity="error",
                        key=None,
                        message=f"unknown tweak group {request.group!r}",
                    ),
                )
            )
        raw.pop(request.group, None)
    else:  # "all"
        raw.clear()

    if raw:
        # Validate surviving entries (catches corruption from manual
        # edits) but write only what's still in ``raw`` — not the
        # registry's resolved values, which would re-emit defaults
        # for keys we just dropped.
        _, diagnostics = validate_persisted_values(
            registry,
            raw,
            source=values_path if values_path.exists() else None,
        )
        errors = tuple(d for d in diagnostics if d.severity == "error")
        if errors:
            raise PlaygroundUpdateError(errors)
        write_persisted_raw(values_path, raw)
    else:
        # No persisted entries left: remove the file entirely so the
        # next render uses spec-code defaults without leaving a stale
        # zero-entry TOML behind.
        if values_path.exists():
            values_path.unlink()

    return load_playground_state(resolved_spec)


def _serialize_declaration(
    decl: TweakDeclaration, value: Any
) -> PlaygroundTweak:
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
        diverged=_values_differ(decl.default, value, kind=decl.kind),
    )


def _values_differ(default: Any, value: Any, *, kind: str) -> bool:
    """Return True iff ``value`` semantically differs from ``default``.

    Handles the normalizations that the persistence layer already applies
    so a round-tripped value is never falsely flagged as edited:

    - Numeric int/float comparison uses :func:`math.isclose` so a stored
      ``58.0`` does not diverge from a declared ``58``.
    - Color tweaks compare case-insensitively (the writer lowercases hex
      via :func:`folio.core.dsl.tweaks.normalize_color`, but a user could
      type ``#D9A64B`` directly into the playground input).
    - Everything else falls back to plain ``!=``.
    """

    if (
        isinstance(default, numbers.Real)
        and not isinstance(default, bool)
        and isinstance(value, numbers.Real)
        and not isinstance(value, bool)
    ):
        return not math.isclose(
            float(default), float(value), rel_tol=1e-9, abs_tol=1e-9
        )
    if kind == "color" and isinstance(default, str) and isinstance(value, str):
        return default.lower() != value.lower()
    return default != value


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
