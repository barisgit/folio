"""`folio skill` command group — install the bundled Folio skill.

The skill installs into an agent-neutral directory so it is not tied to
any one agent tool. Users who want to expose the skill to a specific
client (e.g. Claude Code) can symlink from that client's skills
directory, like:

    ln -s ~/.agents/skills/folio ~/.claude/skills/folio

Two scopes:

- `--scope=user`: `~/.agents/skills/folio/`
- `--scope=project` (default): `<cwd>/.agents/skills/folio/` — literal
  current working directory, with no project-root heuristic.

Install is idempotent: if the destination files already match the
bundled contents, the command is a no-op and exits 0. If any file
differs, the command exits 3 and lists the conflicting paths unless
`--force` is passed, which overwrites in place.
"""

from __future__ import annotations

import shutil
from enum import StrEnum
from pathlib import Path

import typer
from rich.console import Console

from folio.skill import skill_assets, skill_root

_EXIT_OK = 0
_EXIT_OS_ERROR = 1
_EXIT_CONFLICT = 3


class _Scope(StrEnum):
    USER = "user"
    PROJECT = "project"


skill_app = typer.Typer(
    name="skill",
    help="Install the bundled Folio agent skill.",
    no_args_is_help=True,
    rich_markup_mode="rich",
)

_console = Console()
_error_console = Console(stderr=True)


@skill_app.command("install")
def install_command(
    scope: _Scope = typer.Option(
        _Scope.PROJECT, "--scope", case_sensitive=False, help="Installation scope."
    ),
    force: bool = typer.Option(False, "--force", help="Overwrite conflicting files."),
) -> None:
    """Install the Folio skill into an agent-neutral skills directory.

    Writes into `.agents/skills/folio/`. Symlink from a client-specific
    path (e.g. `.claude/skills/folio`) to expose it to that client.
    """
    try:
        destination = _resolve_destination(scope)
    except OSError as exc:
        _error_console.print(f"[red]cannot resolve skill destination:[/red] {exc}")
        raise typer.Exit(code=_EXIT_OS_ERROR) from None

    exit_code = _install_skill(destination, force=force)
    raise typer.Exit(code=exit_code)


SKILL_DIR_PARTS = (".agents", "skills", "folio")


def _resolve_destination(scope: _Scope) -> Path:
    if scope is _Scope.USER:
        home = Path.home()
        if not home.exists():
            raise OSError(f"home directory does not exist: {home}")
        return home.joinpath(*SKILL_DIR_PARTS).resolve()
    return Path.cwd().joinpath(*SKILL_DIR_PARTS).resolve()


def _install_skill(destination: Path, *, force: bool) -> int:
    source = skill_root()
    assets = skill_assets()
    conflicts = _conflicting_files(source, destination, assets)
    if conflicts and not force:
        _error_console.print(
            f"[red]conflicting files at {destination}:[/red]"
        )
        for path in conflicts:
            _error_console.print(f"  {path}")
        _error_console.print(
            "[dim]pass --force to overwrite, or remove the conflicts manually.[/dim]"
        )
        return _EXIT_CONFLICT

    try:
        destination.mkdir(parents=True, exist_ok=True)
        for asset in assets:
            relative = asset.relative_to(source)
            target = destination / relative
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(asset, target)
    except OSError as exc:
        _error_console.print(f"[red]install failed:[/red] {exc}")
        return _EXIT_OS_ERROR

    typer.echo(str(destination))
    return _EXIT_OK


def _conflicting_files(
    source: Path, destination: Path, assets: list[Path]
) -> list[Path]:
    conflicts: list[Path] = []
    for asset in assets:
        relative = asset.relative_to(source)
        target = destination / relative
        if not target.exists():
            continue
        if target.read_bytes() != asset.read_bytes():
            conflicts.append(target)
    return conflicts


__all__ = ["skill_app"]
