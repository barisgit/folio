"""Resolve module-based source locations for DSL symbols.

Source locations are emitted as `module.path:line` strings. That form
resolves identically in the repo and in an installed wheel because it
addresses the defining module via the import system, not via a filesystem
path.

Re-exports (e.g. `folio.dsl.page` → `folio.dsl.builtins:1301`) are unwrapped
to the defining callable before the source line is read.
"""

from __future__ import annotations

import inspect
from typing import Any


class SourceResolutionError(RuntimeError):
    """Raised when a symbol's defining source cannot be determined."""


def _defining_callable(obj: Any) -> Any:
    try:
        return inspect.unwrap(obj)
    except ValueError:
        return obj


def _module_name(obj: Any) -> str:
    mod = inspect.getmodule(obj)
    if mod is not None and mod.__name__:
        return mod.__name__
    module_attr = getattr(obj, "__module__", None)
    if isinstance(module_attr, str) and module_attr:
        return module_attr
    raise SourceResolutionError(f"cannot determine module for {obj!r}")


def resolve_source(obj: Any) -> str:
    """Return the `module.path:line` string for `obj`'s defining source."""
    target = _defining_callable(obj)
    module = _module_name(target)
    try:
        _, lineno = inspect.getsourcelines(target)
    except (OSError, TypeError) as exc:
        raise SourceResolutionError(
            f"cannot determine source line for {module}.{getattr(target, '__qualname__', target)!r}"
        ) from exc
    return f"{module}:{lineno}"


def public_module_for(name: str) -> str:
    """Return the public import module for a DSL `__all__` entry.

    Public imports live under `folio.dsl`, regardless of where the symbol is
    privately defined. Agents should import what the docs tell them to
    import, not what the definition module happens to be.
    """
    _ = name
    return "folio.dsl"
