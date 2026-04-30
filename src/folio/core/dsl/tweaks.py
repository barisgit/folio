"""Design-time tweak declaration model.

Specs declare which design values are user-tunable through helpers in this
module. Persistence (``theme.toml``), validation diagnostics, renderer
integration, and the browser playground are layered on top in later
changes; this module owns the data model only.

Authoring shape::

    from folio.dsl import TextStyle, tweaks

    theme = tweaks.group(
        "theme",
        primary=tweaks.color(default="#d9a64b", label="Primary brand"),
        hero_size_pt=tweaks.size_pt(default=58, min=32, max=76),
    )

    HERO = TextStyle(font_size_pt=theme.hero_size_pt, fill=theme.primary)

Helpers must be invoked inside an active :func:`tweak_context`. Spec
loading wraps the load/render pipeline in such a context; tests can
wrap calls explicitly.

Tags: tweaks, model
"""

from __future__ import annotations

import contextvars
import re
from collections.abc import Iterator, Mapping, Sequence
from contextlib import contextmanager
from dataclasses import dataclass, field
from typing import Any

__all__ = [
    "TweakDeclaration",
    "TweakDiagnostic",
    "TweakGroup",
    "TweakRegistry",
    "TweakValue",
    "choice",
    "color",
    "font_choice",
    "group",
    "letter_spacing",
    "opacity",
    "preset",
    "size_mm",
    "size_pt",
    "stroke_width",
    "tweak_context",
]


# ---------------------------------------------------------------------------
# Internal data model
# ---------------------------------------------------------------------------


_LIVE_MODES = ("live", "rebuild")
_HEX_RE = re.compile(r"^#(?:[0-9a-f]{3}|[0-9a-f]{4}|[0-9a-f]{6}|[0-9a-f]{8})$")
_NAMED_COLOR_RE = re.compile(r"^[a-z]+$")
_COLOR_KEYWORDS = frozenset({"none", "transparent", "currentcolor", "inherit"})


@dataclass(frozen=True, slots=True)
class TweakDeclaration:
    """Frozen schema for one approved design-time tweak.

    Most authors do not construct this class directly. Use
    :func:`group` with helper declarations such as :func:`color` or
    :func:`size_pt`; Folio creates declarations and persists current
    values in ``theme.toml`` next to the spec.

    Tags: tweaks, schema
    """

    key: str
    """Dotted key, e.g. ``"theme.primary"``."""

    group: str
    """Group prefix, e.g. ``"theme"``."""

    name: str
    """Member name within the group, e.g. ``"primary"``."""

    kind: str
    """Helper kind: ``color``, ``size_pt``, ``size_mm``, ``opacity``,
    ``letter_spacing``, ``stroke_width``, ``choice``, ``preset``, or
    ``font_choice``.
    """

    default: Any
    """Default value used when no persisted value is loaded."""

    mode: str
    """Effective edit mode: ``live`` or ``rebuild``."""

    label: str | None = None
    min: float | None = None
    max: float | None = None
    options: tuple[str, ...] | None = None


@dataclass(frozen=True, slots=True)
class TweakDiagnostic:
    """Non-fatal note collected during tweak resolution."""

    severity: str  # "warning" or "error"
    key: str | None
    message: str


# ---------------------------------------------------------------------------
# TweakValue wrapper
# ---------------------------------------------------------------------------


class TweakValue:
    """Resolved tweak value preserving declaration metadata.

    Primitive-coercible via ``__str__``, ``__float__``, ``__int__``, and
    ``__bool__`` so it drops into existing DSL primitives. Live-eligible
    style fields (e.g. :class:`folio.dsl.TextStyle`) preserve the wrapper
    instead of coercing it eagerly, so a future renderer can emit
    ``var(--folio-tweak-...)`` for live attributes.

    The wrapper holds a back-reference to its :class:`TweakRegistry` and
    reads the resolved primitive lazily through it. This makes persisted
    values applied *after* declaration registration visible to wrappers
    that were already handed back to the spec, which is the order of
    operations used by the spec-load pipeline.
    """

    __slots__ = ("_decl", "_registry")

    def __init__(self, declaration: TweakDeclaration, registry: "TweakRegistry") -> None:
        object.__setattr__(self, "_decl", declaration)
        object.__setattr__(self, "_registry", registry)

    # ------ public attributes (read-only) ------

    @property
    def declaration(self) -> TweakDeclaration:
        return self._decl

    @property
    def key(self) -> str:
        return self._decl.key

    @property
    def value(self) -> Any:
        # Read directly from the registry's value mapping rather than going
        # through ``TweakRegistry.resolved`` so a wrapper still works if the
        # declaration was cleared from the registry (e.g. in tests). The
        # declaration itself is pinned on the wrapper for that fallback.
        return self._registry.values.get(self._decl.key, self._decl.default)

    @property
    def mode(self) -> str:
        return self._decl.mode

    @property
    def css_var(self) -> str:
        """CSS custom property name, e.g. ``--folio-tweak-theme-primary``."""

        return f"--folio-tweak-{self._decl.key.replace('.', '-').replace('_', '-')}"

    # ------ primitive coercion ------

    def __str__(self) -> str:
        return str(self.value)

    def __float__(self) -> float:
        return float(self.value)  # type: ignore[arg-type]

    def __int__(self) -> int:
        return int(self.value)  # type: ignore[arg-type]

    def __bool__(self) -> bool:
        return bool(self.value)

    # Numeric protocol: support ``theme.x + 4`` etc. without forcing
    # callers to call ``float(...)`` first. Returning a plain primitive
    # intentionally drops live metadata for the derived value.
    def __add__(self, other: Any) -> Any:
        return self.value + other

    def __radd__(self, other: Any) -> Any:
        return other + self.value

    def __sub__(self, other: Any) -> Any:
        return self.value - other

    def __rsub__(self, other: Any) -> Any:
        return other - self.value

    def __mul__(self, other: Any) -> Any:
        return self.value * other

    def __rmul__(self, other: Any) -> Any:
        return other * self.value

    def __truediv__(self, other: Any) -> Any:
        return self.value / other

    def __rtruediv__(self, other: Any) -> Any:
        return other / self.value

    def __neg__(self) -> Any:
        return -self.value  # type: ignore[operator]

    # ------ identity / equality ------

    def __repr__(self) -> str:
        return f"TweakValue(key={self._decl.key!r}, value={self.value!r}, mode={self._decl.mode!r})"

    def __eq__(self, other: object) -> bool:
        if isinstance(other, TweakValue):
            return self.value == other.value and self._decl.key == other._decl.key
        return self.value == other

    def __hash__(self) -> int:
        # Hash by key only: the resolved primitive can change when
        # ``TweakRegistry.apply_values`` runs, so a value-based hash
        # would invalidate dict/set membership across persistence.
        return hash(self._decl.key)


# ---------------------------------------------------------------------------
# Group proxy
# ---------------------------------------------------------------------------


class TweakGroup:
    """Frozen attribute-access view over a registered tweak group."""

    __slots__ = ("_name", "_members")

    def __init__(self, name: str, members: Mapping[str, TweakValue]) -> None:
        object.__setattr__(self, "_name", name)
        object.__setattr__(self, "_members", dict(members))

    @property
    def name(self) -> str:
        return self._name

    def __getattr__(self, item: str) -> TweakValue:
        members = object.__getattribute__(self, "_members")
        try:
            return members[item]
        except KeyError as exc:
            raise AttributeError(
                f"tweak group {self._name!r} has no member {item!r}"
            ) from exc

    def __iter__(self) -> Iterator[tuple[str, TweakValue]]:
        return iter(self._members.items())

    def __contains__(self, item: object) -> bool:
        return item in self._members

    def __repr__(self) -> str:
        keys = ", ".join(sorted(self._members))
        return f"TweakGroup({self._name!r}, members=[{keys}])"


# ---------------------------------------------------------------------------
# Registry + context
# ---------------------------------------------------------------------------


@dataclass(slots=True)
class TweakRegistry:
    """Spec-scoped collection of tweak declarations and resolved values."""

    declarations: dict[str, TweakDeclaration] = field(default_factory=dict)
    values: dict[str, Any] = field(default_factory=dict)
    diagnostics: list[TweakDiagnostic] = field(default_factory=list)

    def register(self, decl: TweakDeclaration) -> TweakValue:
        if decl.key in self.declarations:
            raise ValueError(
                f"duplicate tweak key: {decl.key!r} is already declared in this spec load"
            )
        self.declarations[decl.key] = decl
        return TweakValue(decl, self)

    def resolved(self, key: str) -> Any:
        if key not in self.declarations:
            raise KeyError(key)
        return self.values.get(key, self.declarations[key].default)

    def apply_values(self, mapping: Mapping[str, Any]) -> None:
        """Store persisted values keyed by dotted tweak key.

        Validation against declarations is added in a later slice; this
        method only records the mapping so that subsequent ``register``
        calls return ``TweakValue`` instances bound to persisted values.
        """

        self.values.update(mapping)

    def snapshot(self) -> "TweakRegistrySnapshot":
        return TweakRegistrySnapshot(
            declarations=tuple(self.declarations.values()),
            values=dict(self.values),
            diagnostics=tuple(self.diagnostics),
        )


@dataclass(frozen=True, slots=True)
class TweakRegistrySnapshot:
    declarations: tuple[TweakDeclaration, ...]
    values: Mapping[str, Any]
    diagnostics: tuple[TweakDiagnostic, ...]


_active: contextvars.ContextVar[TweakRegistry | None] = contextvars.ContextVar(
    "folio_tweak_registry", default=None
)


@contextmanager
def tweak_context(registry: TweakRegistry | None = None) -> Iterator[TweakRegistry]:
    """Bind a fresh :class:`TweakRegistry` for the duration of the block."""

    reg = registry if registry is not None else TweakRegistry()
    token = _active.set(reg)
    try:
        yield reg
    finally:
        _active.reset(token)


def _active_registry() -> TweakRegistry:
    reg = _active.get()
    if reg is None:
        raise RuntimeError(
            "tweak helpers must be called inside a tweak_context(); "
            "Folio activates one automatically during spec load. "
            "Wrap test code in `with tweak_context(): ...`."
        )
    return reg


# ---------------------------------------------------------------------------
# Helper validation
# ---------------------------------------------------------------------------


def _require(default: Any, kind: str) -> None:
    if default is None:
        raise TypeError(
            f"tweaks.{kind}() requires a default value; pass `default=...`"
        )


def _require_numeric(default: Any, kind: str) -> float:
    _require(default, kind)
    if isinstance(default, bool) or not isinstance(default, (int, float)):
        raise TypeError(
            f"tweaks.{kind}() default must be a number, got {type(default).__name__}"
        )
    return float(default)


def _check_range(value: float, *, min: float | None, max: float | None, kind: str) -> None:
    if min is not None and value < min:
        raise ValueError(f"tweaks.{kind}() default {value} is below min={min}")
    if max is not None and value > max:
        raise ValueError(f"tweaks.{kind}() default {value} is above max={max}")


def normalize_color(value: str, *, kind: str) -> str:
    if not isinstance(value, str) or not value:
        raise TypeError(
            f"tweaks.{kind}() default must be a non-empty color string"
        )
    candidate = value.strip().lower()
    if _HEX_RE.match(candidate):
        return candidate
    if candidate in _COLOR_KEYWORDS:
        return candidate
    if _NAMED_COLOR_RE.match(candidate):
        return candidate
    raise ValueError(
        f"tweaks.{kind}() default {value!r} is not a recognised CSS color "
        "(expected a hex string like '#d9a64b' or a CSS color name)"
    )


def _resolve_mode(*, kind: str, default_mode: str, override: str | None) -> str:
    if override is None:
        return default_mode
    if override not in _LIVE_MODES:
        raise ValueError(
            f"tweaks.{kind}() mode must be 'live' or 'rebuild', got {override!r}"
        )
    if override == "live" and default_mode == "rebuild":
        raise ValueError(
            f"tweaks.{kind}() does not support live mode; this tweak class is "
            "rebuild-only because it can affect layout, branching, or asset selection"
        )
    return override


def _normalize_options(options: Sequence[str] | None, *, kind: str) -> tuple[str, ...]:
    if not options:
        raise TypeError(
            f"tweaks.{kind}() requires non-empty `options=(...)`"
        )
    normalized = tuple(options)
    if not all(isinstance(opt, str) and opt for opt in normalized):
        raise TypeError(
            f"tweaks.{kind}() options must be non-empty strings"
        )
    if len(set(normalized)) != len(normalized):
        raise ValueError(f"tweaks.{kind}() options contain duplicates")
    return normalized


# ---------------------------------------------------------------------------
# Public helpers
# ---------------------------------------------------------------------------


# A sentinel returned by individual helpers: the tuple ``(_decl_factory, kwargs)``
# is consumed by ``group()`` to register against the chosen group name.
_PendingDecl = tuple[str, dict[str, Any]]


def color(
    *,
    default: str,
    label: str | None = None,
    mode: str | None = None,
) -> _PendingDecl:
    """Declare an approved color value stored in ``theme.toml``.

    Color tweaks are live-mode by default and resolve to CSS-compatible
    color strings. Use them for sanctioned brand accents that designers
    may tune without duplicating the same value in ``tokens.extend(...)``.

    Args:
        default: Default color string, usually hex such as ``"#d9a64b"``.
        label: Optional human-readable label for tools and docs.
        mode: Optional edit mode override. ``"live"`` is the default;
            ``"rebuild"`` is also allowed.

    Returns:
        _PendingDecl: Pending declaration consumed by :func:`group`.

    Example:
        with tweaks.tweak_context():
            theme = tweaks.group("theme", primary=tweaks.color(default="#d9a64b"))
            str(theme.primary)

    Tags: tweaks, color
    """

    _require(default, "color")
    normalized = normalize_color(default, kind="color")
    effective = _resolve_mode(kind="color", default_mode="live", override=mode)
    return (
        "color",
        {"default": normalized, "label": label, "mode": effective},
    )


def size_pt(
    *,
    default: float | int,
    label: str | None = None,
    min: float | None = None,
    max: float | None = None,
    mode: str | None = None,
) -> _PendingDecl:
    """Declare a typographic size tweak in points (live by default)."""

    value = _require_numeric(default, "size_pt")
    _check_range(value, min=min, max=max, kind="size_pt")
    effective = _resolve_mode(kind="size_pt", default_mode="live", override=mode)
    return (
        "size_pt",
        {"default": value, "label": label, "min": min, "max": max, "mode": effective},
    )


def size_mm(
    *,
    default: float | int,
    label: str | None = None,
    min: float | None = None,
    max: float | None = None,
    mode: str | None = None,
) -> _PendingDecl:
    """Declare a layout size tweak in millimetres (rebuild by default)."""

    value = _require_numeric(default, "size_mm")
    _check_range(value, min=min, max=max, kind="size_mm")
    effective = _resolve_mode(kind="size_mm", default_mode="rebuild", override=mode)
    return (
        "size_mm",
        {"default": value, "label": label, "min": min, "max": max, "mode": effective},
    )


def opacity(
    *,
    default: float | int,
    label: str | None = None,
    min: float | None = 0.0,
    max: float | None = 1.0,
    mode: str | None = None,
) -> _PendingDecl:
    """Declare an opacity tweak in [0, 1] (live by default)."""

    value = _require_numeric(default, "opacity")
    _check_range(value, min=min, max=max, kind="opacity")
    effective = _resolve_mode(kind="opacity", default_mode="live", override=mode)
    return (
        "opacity",
        {"default": value, "label": label, "min": min, "max": max, "mode": effective},
    )


def letter_spacing(
    *,
    default: float | int,
    label: str | None = None,
    min: float | None = None,
    max: float | None = None,
    mode: str | None = None,
) -> _PendingDecl:
    """Declare a letter-spacing tweak in points (live by default)."""

    value = _require_numeric(default, "letter_spacing")
    _check_range(value, min=min, max=max, kind="letter_spacing")
    effective = _resolve_mode(kind="letter_spacing", default_mode="live", override=mode)
    return (
        "letter_spacing",
        {"default": value, "label": label, "min": min, "max": max, "mode": effective},
    )


def stroke_width(
    *,
    default: float | int,
    label: str | None = None,
    min: float | None = None,
    max: float | None = None,
    mode: str | None = None,
) -> _PendingDecl:
    """Declare a presentation stroke-width tweak (live by default)."""

    value = _require_numeric(default, "stroke_width")
    _check_range(value, min=min, max=max, kind="stroke_width")
    effective = _resolve_mode(kind="stroke_width", default_mode="live", override=mode)
    return (
        "stroke_width",
        {"default": value, "label": label, "min": min, "max": max, "mode": effective},
    )


def choice(
    *,
    default: str,
    options: Sequence[str],
    label: str | None = None,
    mode: str | None = None,
) -> _PendingDecl:
    """Declare a choice tweak from a fixed option list (rebuild by default)."""

    return _build_choice("choice", default=default, options=options, label=label, mode=mode)


def preset(
    *,
    default: str,
    options: Sequence[str],
    label: str | None = None,
    mode: str | None = None,
) -> _PendingDecl:
    """Declare a preset tweak (rebuild by default)."""

    return _build_choice("preset", default=default, options=options, label=label, mode=mode)


def font_choice(
    *,
    default: str,
    options: Sequence[str],
    label: str | None = None,
    mode: str | None = None,
) -> _PendingDecl:
    """Declare a font-family choice tweak (rebuild by default)."""

    return _build_choice("font_choice", default=default, options=options, label=label, mode=mode)


def _build_choice(
    kind: str,
    *,
    default: str,
    options: Sequence[str],
    label: str | None,
    mode: str | None,
) -> _PendingDecl:
    _require(default, kind)
    if not isinstance(default, str) or not default:
        raise TypeError(f"tweaks.{kind}() default must be a non-empty string")
    normalized = _normalize_options(options, kind=kind)
    if default not in normalized:
        raise ValueError(
            f"tweaks.{kind}() default {default!r} is not in options {normalized!r}"
        )
    effective = _resolve_mode(kind=kind, default_mode="rebuild", override=mode)
    return (kind, {"default": default, "label": label, "options": normalized, "mode": effective})


# ---------------------------------------------------------------------------
# Group helper
# ---------------------------------------------------------------------------


def group(name: str, **members: _PendingDecl) -> TweakGroup:
    """Register a named group of tweaks and return an attribute-access view.

    Each keyword argument must be a value returned by another helper such
    as :func:`color`, :func:`size_pt`, or :func:`choice`. The dotted key
    becomes ``f"{name}.{member}"``.
    """

    if not isinstance(name, str) or not name or not name.replace("_", "").isalnum():
        raise ValueError(
            f"tweaks.group() name must be a non-empty alphanumeric/underscore "
            f"identifier, got {name!r}"
        )
    if not members:
        raise TypeError("tweaks.group() requires at least one member")

    registry = _active_registry()
    resolved: dict[str, TweakValue] = {}
    for member_name, pending in members.items():
        if not (isinstance(pending, tuple) and len(pending) == 2):
            raise TypeError(
                f"tweaks.group() member {member_name!r} must be the result of a "
                "tweak helper such as tweaks.color(...) or tweaks.size_pt(...)"
            )
        kind, kwargs = pending
        decl = TweakDeclaration(
            key=f"{name}.{member_name}",
            group=name,
            name=member_name,
            kind=kind,
            **kwargs,
        )
        resolved[member_name] = registry.register(decl)
    return TweakGroup(name, resolved)
