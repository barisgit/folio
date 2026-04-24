"""`folio create` command — thin IO adapter."""

from __future__ import annotations

import re
from importlib import resources
from importlib.resources.abc import Traversable
from pathlib import Path
from typing import Annotated

import typer
from rich.console import Console

console = Console()

JINJA_SUFFIXES = (".j2", ".jinja", ".jinja2")
IGNORED_TEMPLATE_FILES = {"template.yaml"}
IGNORED_TEMPLATE_DIRS = frozenset(
    {
        "__pycache__",
        ".pytest_cache",
        ".ruff_cache",
        ".mypy_cache",
        ".ty_cache",
        ".venv",
        "out",
        ".cache",
    }
)
IGNORED_TEMPLATE_SUFFIXES = (".pyc", ".pyo")

_SLUG_INVALID_RE = re.compile(r"[^a-z0-9-]+")


def _default_project_slug(target_dir: Path) -> str:
    raw = target_dir.name.strip().lower()
    slug = _SLUG_INVALID_RE.sub("-", raw).strip("-")
    return slug or "my-folio-project"


def _parse_vars(var_args: list[str] | None) -> dict[str, str]:
    variables: dict[str, str] = {}
    if not var_args:
        return variables
    for item in var_args:
        if "=" not in item:
            console.print(f"[red]Invalid --var format:[/red] {item!r} (expected key=value)")
            raise typer.Exit(1)
        key, _, value = item.partition("=")
        variables[key] = value
    return variables


def _strip_suffix(name: str) -> str:
    for suffix in JINJA_SUFFIXES:
        if name.endswith(suffix):
            return name[: -len(suffix)]
    return name


def _is_template_file(name: str) -> bool:
    return any(name.endswith(suffix) for suffix in JINJA_SUFFIXES)


def _render_jinja(text: str, variables: dict[str, str]) -> str:
    from jinja2 import Environment, StrictUndefined

    env = Environment(undefined=StrictUndefined)
    template = env.from_string(text)
    return template.render(**variables)


def _builtin_template_root() -> Traversable:
    return resources.files("folio").joinpath("templates").joinpath("starter")


def _should_skip_entry(name: str, *, is_dir: bool) -> bool:
    if is_dir and name in IGNORED_TEMPLATE_DIRS:
        return True
    if not is_dir and name in IGNORED_TEMPLATE_FILES:
        return True
    if not is_dir and name.endswith(IGNORED_TEMPLATE_SUFFIXES):
        return True
    return False


def _copy_template(source_dir: Traversable, target_dir: Path, variables: dict[str, str]) -> None:
    for child in sorted(source_dir.iterdir(), key=lambda entry: entry.name):
        if _should_skip_entry(child.name, is_dir=child.is_dir()):
            continue

        rendered_name = _strip_suffix(_render_jinja(child.name, variables))
        target_path = target_dir / rendered_name

        if child.is_dir():
            target_path.mkdir(parents=True, exist_ok=True)
            _copy_template(child, target_path, variables)
            continue

        target_path.parent.mkdir(parents=True, exist_ok=True)
        if _is_template_file(child.name):
            rendered_content = _render_jinja(child.read_text(encoding="utf-8"), variables)
            target_path.write_text(rendered_content, encoding="utf-8")
        else:
            target_path.write_bytes(child.read_bytes())
        console.print(f"created [green]{target_path}[/green]")


def _install_starter_skill(target_dir: Path) -> None:
    import shutil

    SKILL_DIR_PARTS = (".agents", "skills", "folio")
    from folio.skill import skill_assets, skill_root

    source = skill_root()
    destination = target_dir.joinpath(*SKILL_DIR_PARTS)
    destination.mkdir(parents=True, exist_ok=True)
    for asset in skill_assets():
        relative = asset.relative_to(source)
        target_path = destination / relative
        target_path.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(asset, target_path)
    console.print(f"installed skill at [green]{destination}[/green]")


def create_command(
    target_dir: Annotated[
        Path,
        typer.Argument(help="Path to the new project directory", exists=False),
    ],
    var: Annotated[
        list[str] | None,
        typer.Option("--var", help="Template variables as key=value pairs"),
    ] = None,
    no_skill: Annotated[
        bool,
        typer.Option("--no-skill", help="Skip installing the bundled Folio skill."),
    ] = False,
) -> None:
    starter_template = _builtin_template_root()
    if not starter_template.is_dir():
        console.print("[red]Built-in starter template is not available in this installation.[/red]")
        raise typer.Exit(1)

    target_dir = target_dir.expanduser()

    if target_dir.exists():
        if not target_dir.is_dir():
            console.print(f"[red]Target path exists and is not a directory:[/red] {target_dir}")
            raise typer.Exit(1)
        if any(target_dir.iterdir()):
            console.print(f"[red]Target directory is not empty:[/red] {target_dir}")
            raise typer.Exit(1)

    variables = _parse_vars(var)
    variables.setdefault("project_slug", _default_project_slug(target_dir))

    try:
        target_dir.mkdir(parents=True, exist_ok=True)
        _copy_template(starter_template, target_dir, variables)
        if not no_skill:
            _install_starter_skill(target_dir)
    except typer.Exit:
        raise
    except Exception as exc:
        console.print(f"[red]Create error:[/red] {exc}")
        raise typer.Exit(1) from exc

    console.print(f"Done! Starter project created in [cyan]{target_dir}[/cyan]")
