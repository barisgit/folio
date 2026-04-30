"""Spec-load + render orchestrator that wires tweak persistence.

This is the helper ``folio validate`` and ``folio build`` route through
once tweak persistence exists. It owns the order of operations so
:class:`~folio.core.dsl.tweaks.TweakValue` wrappers issued during spec
load see persisted values from ``<spec_dir>/theme.toml`` before any
rendering happens.

Order of operations:

1. Read raw TOML from ``<spec_dir>/theme.toml`` (parse errors surface
   as :class:`TweakValuesError` before the spec is loaded).
2. Enter a fresh :class:`TweakRegistry` via ``tweak_context``.
3. Run ``load_dsl_module`` so declarations register into the registry.
4. Validate the raw mapping against declarations and apply the
   validated mapping to the registry; warnings (unknown keys) are
   collected, errors abort with :class:`TweakValidationError` before
   rendering.
5. Render the collection in the existing build mode.

Slice 3 of ``add-tweaks-model``. The renderer mode flag arrives in
slice 4 and will plug into step 5 without changing the helper's public
signature.

Tags: tweaks, services
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path

from folio.core.dsl.loader import load_dsl_module
from folio.core.dsl.tweak_values import (
    TweakValuesError,
    load_persisted_values,
    resolve_values_file,
    validate_persisted_values,
)
from folio.core.dsl.tweaks import (
    TweakDiagnostic,
    TweakRegistry,
    TweakRegistrySnapshot,
    tweak_context,
)
from folio.core.render.pipeline import (
    BuildResult,
    RenderMode,
    collection_from_module,
    render_collection,
    validate_document,
)

__all__ = [
    "SpecLoadResult",
    "SpecValidateResult",
    "TweakValidationError",
    "load_spec_with_tweaks",
    "validate_spec_with_tweaks",
]


class TweakValidationError(Exception):
    """Raised when persisted tweak values fail declaration validation.

    Carries the offending diagnostics so CLI adapters can render one
    line per problem. Warning-level diagnostics never raise; only
    error-level diagnostics do.
    """

    def __init__(self, diagnostics: Sequence[TweakDiagnostic]) -> None:
        self.diagnostics: tuple[TweakDiagnostic, ...] = tuple(diagnostics)
        first = next(iter(diagnostics), None)
        head = first.message if first is not None else "tweak validation failed"
        super().__init__(head)


@dataclass(frozen=True, slots=True)
class SpecLoadResult:
    """Outcome of :func:`load_spec_with_tweaks`."""

    result: BuildResult
    snapshot: TweakRegistrySnapshot
    diagnostics: tuple[TweakDiagnostic, ...]


@dataclass(frozen=True, slots=True)
class SpecValidateResult:
    """Outcome of :func:`validate_spec_with_tweaks`."""

    snapshot: TweakRegistrySnapshot
    diagnostics: tuple[TweakDiagnostic, ...]


def load_spec_with_tweaks(
    spec_path: Path, *, render_mode: RenderMode = "build"
) -> SpecLoadResult:
    """Load ``spec_path`` through a tweak context and render its collection.

    Raises :class:`TweakValuesError` when the values file cannot be
    parsed, :class:`TweakValidationError` when persisted values violate
    their declarations, and propagates ``DslError`` / ``RenderError``
    from the underlying pipeline. ``render_mode`` defaults to concrete
    build output; the playground service passes ``"playground"`` without
    changing build behavior.
    """

    values_path = resolve_values_file(spec_path)
    raw = load_persisted_values(values_path)

    registry = TweakRegistry()
    with tweak_context(registry):
        module = load_dsl_module(spec_path)
        validated, diagnostics = validate_persisted_values(
            registry,
            raw,
            source=values_path if raw is not None else None,
        )
        registry.apply_values(validated)

        errors = tuple(d for d in diagnostics if d.severity == "error")
        if errors:
            raise TweakValidationError(errors)

        collection = collection_from_module(module)
        result = render_collection(
            collection,
            config_dir=spec_path.parent,
            source_path=spec_path,
            mode=render_mode,
        )

    return SpecLoadResult(
        result=result,
        snapshot=registry.snapshot(),
        diagnostics=tuple(diagnostics),
    )


def validate_spec_with_tweaks(spec_path: Path) -> SpecValidateResult:
    """Load ``spec_path`` and run document validation without rendering.

    Mirrors :func:`load_spec_with_tweaks` but stops after
    ``validate_document`` so ``folio validate`` does not pay for SVG
    rendering. Raises the same exceptions as the rendering helper.
    """

    values_path = resolve_values_file(spec_path)
    raw = load_persisted_values(values_path)

    registry = TweakRegistry()
    with tweak_context(registry):
        module = load_dsl_module(spec_path)
        validated, diagnostics = validate_persisted_values(
            registry,
            raw,
            source=values_path if raw is not None else None,
        )
        registry.apply_values(validated)

        errors = tuple(d for d in diagnostics if d.severity == "error")
        if errors:
            raise TweakValidationError(errors)

        for document in collection_from_module(module).documents:
            validate_document(document)

    return SpecValidateResult(
        snapshot=registry.snapshot(),
        diagnostics=tuple(diagnostics),
    )
