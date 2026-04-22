"""Target resolution for the check command."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from folio.dsl.loader import resolve_spec_path


@dataclass(frozen=True)
class CheckTarget:
    """Resolved target for the check pipeline."""

    spec_path: Path
    project_root: Path


def resolve_check_target(target: Path | None) -> CheckTarget:
    """Resolve a CLI target into a spec path and project root.

    - None → cwd/build.py, project_root = cwd
    - directory → dir/build.py, project_root = dir
    - file → file as spec, project_root = file.parent
    """
    if target is None:
        project_root = Path.cwd().expanduser().resolve()
        spec_path = resolve_spec_path(project_root)
    else:
        resolved = target.expanduser().resolve()
        if resolved.is_dir():
            project_root = resolved
            spec_path = resolve_spec_path(resolved)
        else:
            project_root = resolved.parent
            spec_path = resolve_spec_path(resolved)
    return CheckTarget(spec_path=spec_path, project_root=project_root)
