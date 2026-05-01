"""Generate ``api.generated.ts`` from the playground's Pydantic models.

The generated file lives at ``src/folio/playground_ui/api.generated.ts``
and is consumed by the browser playground source so the wire format is
strictly typed at the TS boundary.

The generator is deliberately small and dependency-free (beyond Pydantic
v2 itself). It traverses the Pydantic JSON schema and emits a stable,
readable TypeScript declaration with deterministic ordering.

Run via the build script::

    bun run build:playground

or directly::

    uv run python -m folio._dev.gen_playground_types
"""

from __future__ import annotations

import sys
from collections.abc import Mapping
from pathlib import Path
from typing import Any

from folio.services.playground import (
    Diagnostic,
    PlaygroundPage,
    PlaygroundState,
    PlaygroundTweak,
    TweakUpdateRequest,
)

# The order here is the order in which interfaces appear in the generated
# file. Sort within a group only when correctness allows; declaration
# order is meaningful for human readers and code review.
_MODELS = (
    Diagnostic,
    PlaygroundPage,
    PlaygroundTweak,
    PlaygroundState,
    TweakUpdateRequest,
)

_HEADER = (
    "// AUTO-GENERATED - do not edit. Run `bun run build:playground` to "
    "regenerate this file.\n"
    "// Source: src/folio/_dev/gen_playground_types.py\n"
    "\n"
)


def _ts_for_python_type(annotation: Any) -> str:
    """Best-effort Python annotation -> TypeScript expression.

    Handles only the shapes used by the playground payload models. Falls
    back to ``unknown`` when the mapping is genuinely undecidable.
    """

    import types
    import typing

    origin = typing.get_origin(annotation)
    args = typing.get_args(annotation)

    if annotation is type(None):
        return "null"
    if annotation is Any:
        return "unknown"
    if annotation is str:
        return "string"
    if annotation in (int, float):
        return "number"
    if annotation is bool:
        return "boolean"
    if annotation is bytes:
        return "string"
    if annotation is Path:
        return "string"  # serialized as path string by mode='json'

    # Union / Optional. Sort union members for stable output.
    if origin in (typing.Union, types.UnionType):
        members = sorted({_ts_for_python_type(a) for a in args})
        # ``X | None`` stays as ``X | null`` but keep ordering stable.
        return " | ".join(members)

    if origin in (list, tuple, set, frozenset):
        if origin is tuple and len(args) == 2 and args[1] is Ellipsis:
            inner = _ts_for_python_type(args[0])
            return f"{inner}[]"
        if not args:
            return "unknown[]"
        # tuple[A, B] -> [A, B]; otherwise treat as homogeneous list.
        if origin is tuple and Ellipsis not in args:
            members = ", ".join(_ts_for_python_type(a) for a in args)
            return f"[{members}]"
        inner = _ts_for_python_type(args[0])
        return f"{inner}[]"

    if origin in (dict, Mapping) or origin is typing.Mapping:
        _ts_for_python_type(args[0]) if args else "string"
        val_t = _ts_for_python_type(args[1]) if len(args) > 1 else "unknown"
        # JS object keys are always string-coerced.
        return f"Record<string, {val_t}>"

    # Pydantic BaseModel reference -> emit by class name.
    try:
        from pydantic import BaseModel

        if isinstance(annotation, type) and issubclass(annotation, BaseModel):
            return annotation.__name__
    except Exception:
        pass

    return "unknown"


def _interface_for_model(model: type) -> str:
    """Render one TypeScript interface from a Pydantic model class.

    Field declaration order matches the Pydantic field declaration order,
    which is also the camelCase order users see in the wire JSON.
    """

    lines = [f"export interface {model.__name__} {{"]
    for field_name, field_info in model.model_fields.items():
        wire_name = field_info.alias or field_name
        ts_type = _ts_for_python_type(field_info.annotation)
        # A field is optional in TS (``key?:``) only when the wire JSON
        # may omit the key. Pydantic's ``model_dump`` always emits every
        # declared field, so we never mark fields optional here; nullable
        # values are expressed as ``| null`` instead. The sole exception
        # is ``TweakUpdateRequest`` whose two shapes share fields: there
        # we mark all top-level fields optional via the dedicated path
        # below.
        optional = "?" if model is TweakUpdateRequest else ""
        lines.append(f"  {wire_name}{optional}: {ts_type};")
    lines.append("}")
    return "\n".join(lines)


def render_typescript() -> str:
    """Build the full ``api.generated.ts`` content as a string."""

    blocks = [_interface_for_model(model) for model in _MODELS]
    body = "\n\n".join(blocks) + "\n"
    return _HEADER + body


# Final wire path, repo-relative.
_OUTPUT_PATH = Path("src/folio/playground_ui/api.generated.ts")


def main(argv: list[str] | None = None) -> int:
    argv = argv if argv is not None else sys.argv[1:]
    check_only = "--check" in argv

    repo_root = Path(__file__).resolve().parents[3]
    target = repo_root / _OUTPUT_PATH
    new = render_typescript()
    # Always LF, never CRLF.
    new = new.replace("\r\n", "\n")

    if check_only:
        if not target.exists() or target.read_text(encoding="utf-8") != new:
            sys.stderr.write(
                f"{_OUTPUT_PATH} is out of date. Run `bun run build:playground`.\n",
            )
            return 1
        return 0

    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(new, encoding="utf-8", newline="\n")
    return 0


if __name__ == "__main__":  # pragma: no cover - CLI entry
    raise SystemExit(main())
