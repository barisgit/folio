from __future__ import annotations

import importlib.util
import sys
import types
from contextlib import suppress
from hashlib import sha256
from pathlib import Path

from folio.dsl import builtins as dsl_builtins


class DslError(Exception):
    """Raised when a DSL module cannot be loaded."""


_DEFAULT_SPEC_FILENAME = Path("build.py")


def default_spec_path(cwd: Path | None = None) -> Path:
    base = (cwd or Path.cwd()).expanduser().resolve()
    return base / _DEFAULT_SPEC_FILENAME



def resolve_spec_path(path: Path | None = None) -> Path:
    if path is None:
        return default_spec_path()
    resolved = path.expanduser().resolve()
    if resolved.is_dir():
        return default_spec_path(resolved)
    return resolved



def load_dsl_module(path: Path) -> types.ModuleType:
    resolved = path.expanduser().resolve()
    if resolved.suffix != ".py":
        raise DslError(f"DSL path must be a Python file: {resolved}")
    if not resolved.exists():
        raise DslError(f"DSL file not found: {resolved}")

    module_name = f"folio_user_dsl_{sha256(str(resolved).encode('utf-8')).hexdigest()[:12]}"
    spec = importlib.util.spec_from_file_location(module_name, resolved)
    if spec is None or spec.loader is None:
        raise DslError(f"Could not import DSL module from {resolved}")

    module = importlib.util.module_from_spec(spec)
    dsl_builtins.reset_auto_ids()
    import folio.dsl as dsl_package
    from folio.dsl import charts as dsl_charts

    dsl_package.render = dsl_builtins.render
    original_sys_path = list(sys.path)
    sys.modules[module_name] = module
    sys.path.insert(0, str(resolved.parent))
    dsl_charts.set_spec_base_dir(resolved.parent)
    try:
        spec.loader.exec_module(module)
    except SyntaxError as exc:
        raise DslError(f"Syntax error in {resolved}:{exc.lineno}: {exc.msg}") from exc
    except Exception as exc:
        raise DslError(f"Failed to load DSL module {resolved}: {exc}") from exc
    finally:
        sys.path[:] = original_sys_path
        with suppress(KeyError):
            del sys.modules[module_name]

    return module
