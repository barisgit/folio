"""TOML-backed persistence for design-time tweak values.

This module owns:

- Resolving the values file path beside a spec (``<spec_dir>/theme.toml``).
- Reading the file with :mod:`tomllib`.
- Validating persisted values against a populated :class:`TweakRegistry`
  and emitting :class:`TweakDiagnostic` entries for type, range, option,
  and unknown-key violations.
- Applying validated values back onto the registry so already-issued
  :class:`TweakValue` wrappers see the persisted primitives.
- Writing a deterministic TOML file from the registry's current state.

Slice 2 of ``add-tweaks-model``. CLI/render integration arrives in later
slices and must call :func:`apply_persisted_values` after the spec
module has been loaded so wrappers see persisted values.

Tags: tweaks, persistence
"""

from __future__ import annotations

import tomllib
from collections.abc import Mapping
from pathlib import Path
from typing import Any

from folio.core.dsl.tweaks import (
    TweakDeclaration,
    TweakDiagnostic,
    TweakRegistry,
    normalize_color,
)

__all__ = [
    "TweakValuesError",
    "apply_persisted_values",
    "load_persisted_values",
    "resolve_values_file",
    "validate_persisted_values",
    "write_persisted_raw",
    "write_persisted_values",
]


# ---------------------------------------------------------------------------
# Exceptions
# ---------------------------------------------------------------------------


class TweakValuesError(Exception):
    """Raised on TOML parse failures or malformed values files.

    Validation errors against tweak declarations are surfaced as
    :class:`TweakDiagnostic` entries instead, so a single bad value never
    aborts the whole load.
    """


# ---------------------------------------------------------------------------
# File resolution + loading
# ---------------------------------------------------------------------------


def resolve_values_file(spec_path: Path) -> Path:
    """Return the path of the persisted values file for ``spec_path``.

    The default values file lives beside the resolved spec at
    ``<spec_dir>/theme.toml``. There is no override knob in this slice;
    callers that need a different layout should resolve the spec to the
    parent of their preferred values file.
    """

    return spec_path.parent / "theme.toml"


def load_persisted_values(
    path: Path,
) -> Mapping[str, Mapping[str, Any]] | None:
    """Read ``path`` as the persisted tweak values mapping.

    Returns ``None`` when the file does not exist; callers fall back to
    declaration defaults in that case. Raises :class:`TweakValuesError`
    when the file is unparseable or contains top-level scalars (every
    persisted value must live under a ``[group]`` table).
    """

    if not path.exists():
        return None
    try:
        with path.open("rb") as handle:
            raw = tomllib.load(handle)
    except tomllib.TOMLDecodeError as exc:
        raise TweakValuesError(
            f"failed to parse tweak values file {path}: {exc}"
        ) from exc

    for key, value in raw.items():
        if not isinstance(value, dict):
            raise TweakValuesError(
                f"tweak values file {path} has top-level scalar {key!r}; "
                "persisted values must live under a [group] table"
            )
    return raw


# ---------------------------------------------------------------------------
# Validation
# ---------------------------------------------------------------------------


_NUMERIC_KINDS = frozenset(
    {"size_pt", "size_mm", "opacity", "letter_spacing", "stroke_width"}
)
_CHOICE_KINDS = frozenset({"choice", "preset", "font_choice"})


def validate_persisted_values(
    registry: TweakRegistry,
    raw: Mapping[str, Mapping[str, Any]] | None,
    *,
    source: Path | None,
) -> tuple[dict[str, Any], list[TweakDiagnostic]]:
    """Validate ``raw`` against ``registry`` declarations.

    Returns ``(validated, diagnostics)``. ``validated`` keeps only values
    that match their declaration. ``diagnostics`` are also appended to
    ``registry.diagnostics`` so the spec-load helper sees a unified
    diagnostic stream.
    """

    diagnostics: list[TweakDiagnostic] = []
    validated: dict[str, Any] = {}

    if raw is None:
        return validated, diagnostics

    src = f" in {source}" if source is not None else ""
    for table_name, table in raw.items():
        for member_name, value in table.items():
            dotted = f"{table_name}.{member_name}"
            decl = registry.declarations.get(dotted)
            if decl is None:
                diagnostics.append(
                    TweakDiagnostic(
                        severity="warning",
                        key=dotted,
                        message=f"unknown persisted tweak key {dotted!r}{src}",
                    )
                )
                continue
            ok, normalized, message = _coerce_value(decl, value)
            if not ok:
                diagnostics.append(
                    TweakDiagnostic(
                        severity="error",
                        key=dotted,
                        message=f"{message}{src}",
                    )
                )
                continue
            validated[dotted] = normalized

    registry.diagnostics.extend(diagnostics)
    return validated, diagnostics


def _coerce_value(
    decl: TweakDeclaration, value: Any
) -> tuple[bool, Any, str]:
    """Coerce ``value`` for ``decl``. Return ``(ok, normalized, message)``.

    ``message`` is the error text when ``ok`` is False; otherwise ``""``.
    """

    kind = decl.kind
    if kind in _NUMERIC_KINDS:
        if isinstance(value, bool) or not isinstance(value, (int, float)):
            return (
                False,
                None,
                f"tweak {decl.key!r} expects a number for kind {kind!r}, "
                f"got {type(value).__name__} {value!r}",
            )
        numeric = float(value)
        if decl.min is not None and numeric < decl.min:
            return (
                False,
                None,
                f"tweak {decl.key!r} value {numeric} is below min={decl.min} "
                f"(allowed range {decl.min}..{decl.max})",
            )
        if decl.max is not None and numeric > decl.max:
            return (
                False,
                None,
                f"tweak {decl.key!r} value {numeric} is above max={decl.max} "
                f"(allowed range {decl.min}..{decl.max})",
            )
        return True, numeric, ""

    if kind == "color":
        if not isinstance(value, str):
            return (
                False,
                None,
                f"tweak {decl.key!r} expects a color string, "
                f"got {type(value).__name__} {value!r}",
            )
        try:
            normalized = normalize_color(value, kind="color")
        except (TypeError, ValueError) as exc:
            return (
                False,
                None,
                f"tweak {decl.key!r} has invalid color value {value!r}: {exc}",
            )
        return True, normalized, ""

    if kind in _CHOICE_KINDS:
        if not isinstance(value, str):
            return (
                False,
                None,
                f"tweak {decl.key!r} expects one of {decl.options!r}, "
                f"got {type(value).__name__} {value!r}",
            )
        if decl.options is None or value not in decl.options:
            return (
                False,
                None,
                f"tweak {decl.key!r} value {value!r} is not in options {decl.options!r}",
            )
        return True, value, ""

    return (
        False,
        None,
        f"tweak {decl.key!r} has unsupported kind {kind!r} for persistence",
    )


# ---------------------------------------------------------------------------
# Orchestration
# ---------------------------------------------------------------------------


def apply_persisted_values(
    registry: TweakRegistry, spec_path: Path
) -> list[TweakDiagnostic]:
    """Resolve, load, validate, and apply persisted values for ``spec_path``.

    The spec module must already have been executed under ``registry``
    so declarations exist when validation runs. After this call, every
    :class:`TweakValue` issued during spec load resolves through the new
    persisted values automatically.
    """

    path = resolve_values_file(spec_path)
    raw = load_persisted_values(path)
    validated, diagnostics = validate_persisted_values(
        registry, raw, source=path if raw is not None else None
    )
    registry.apply_values(validated)
    return diagnostics


# ---------------------------------------------------------------------------
# Deterministic writer
# ---------------------------------------------------------------------------


def write_persisted_values(path: Path, registry: TweakRegistry) -> None:
    """Write ``registry`` state to ``path`` as deterministic TOML.

    Groups are sorted alphabetically; declarations within a group are
    sorted by member name. Values come from
    :meth:`TweakRegistry.resolved` so an unedited registry round-trips
    its declaration defaults. Comments and pre-existing formatting are
    not preserved: ``theme.toml`` is a Folio-managed values file.
    """

    grouped: dict[str, list[TweakDeclaration]] = {}
    for decl in registry.declarations.values():
        grouped.setdefault(decl.group, []).append(decl)

    lines: list[str] = []
    for group_name in sorted(grouped):
        members = sorted(grouped[group_name], key=lambda d: d.name)
        lines.append(f"[{group_name}]")
        for decl in members:
            value = registry.resolved(decl.key)
            lines.append(f"{decl.name} = {_format_value(value)}")
        lines.append("")  # trailing blank line per group

    if lines:
        # Drop the final blank between the last group and EOF, replace
        # it with a single trailing newline.
        while lines and lines[-1] == "":
            lines.pop()
        text = "\n".join(lines) + "\n"
    else:
        text = ""

    path.write_text(text, encoding="utf-8")


def write_persisted_raw(
    path: Path, raw: Mapping[str, Mapping[str, Any]]
) -> None:
    """Write only the entries in ``raw`` to ``path`` as deterministic TOML.

    Unlike :func:`write_persisted_values`, this does not consult a
    registry: it serialises exactly the groups/members supplied,
    skipping empty groups. Used by reset flows that have already
    pruned persisted entries and need the file to reflect that
    pruning rather than re-emit defaults for every declaration.
    """

    lines: list[str] = []
    for group_name in sorted(raw):
        members = raw[group_name]
        if not members:
            continue
        lines.append(f"[{group_name}]")
        for member_name in sorted(members):
            lines.append(
                f"{member_name} = {_format_value(members[member_name])}"
            )
        lines.append("")

    if lines:
        while lines and lines[-1] == "":
            lines.pop()
        text = "\n".join(lines) + "\n"
    else:
        text = ""

    path.write_text(text, encoding="utf-8")


def _format_value(value: Any) -> str:
    """Format a primitive Python value as a TOML literal.

    Supported: ``str``, ``int``, ``float``, ``bool``, and ``list``/
    ``tuple`` of strings. Reserved for future tweak helpers that want to
    persist option arrays.
    """

    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, int):
        return repr(value)
    if isinstance(value, float):
        return repr(value)
    if isinstance(value, str):
        return _format_string(value)
    if isinstance(value, (list, tuple)):
        if not all(isinstance(item, str) for item in value):
            raise TypeError(
                f"tweak values writer only supports string arrays, got {value!r}"
            )
        inner = ", ".join(_format_string(item) for item in value)
        return f"[{inner}]"
    raise TypeError(
        f"tweak values writer cannot serialise value {value!r} of type "
        f"{type(value).__name__}"
    )


def _format_string(value: str) -> str:
    escaped = value.replace("\\", "\\\\").replace('"', '\\"')
    return f'"{escaped}"'
