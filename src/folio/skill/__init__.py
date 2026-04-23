"""Bundled Claude Code skill for working with Folio projects.

The skill directory lives beside this module as file assets (`SKILL.md` and
companions). Code under this package never imports those files directly;
it only locates them via :func:`skill_root` so the `folio skill install`
command can copy them into a Claude Code skills directory.
"""

from __future__ import annotations

from pathlib import Path


def skill_root() -> Path:
    """Return the absolute path to the bundled skill directory."""
    return Path(__file__).resolve().parent


def skill_assets() -> list[Path]:
    """Return every regular file that makes up the bundled skill."""
    root = skill_root()
    return sorted(
        path
        for path in root.rglob("*")
        if path.is_file() and path.name != "__init__.py" and not path.name.endswith(".pyc")
    )


__all__ = ["skill_assets", "skill_root"]
