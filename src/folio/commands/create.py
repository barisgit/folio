from __future__ import annotations

from importlib import resources
from importlib.resources.abc import Traversable
from pathlib import Path
from typing import Annotated

import typer
from rich.console import Console

console = Console()

JINJA_SUFFIXES = (".j2", ".jinja", ".jinja2")
IGNORED_TEMPLATE_FILES = {"template.yaml"}


def _parse_vars(var_args: list[str] | None) -> dict[str, str]:
    """Parse --var key=value pairs into a dict."""
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
    """Remove the template suffix from a filename."""
    for suffix in JINJA_SUFFIXES:
        if name.endswith(suffix):
            return name[: -len(suffix)]
    return name


def _is_template_file(name: str) -> bool:
    return any(name.endswith(suffix) for suffix in JINJA_SUFFIXES)


def _render_jinja(text: str, variables: dict[str, str]) -> str:
    """Render a Jinja2 template string with strict undefined."""
    from jinja2 import Environment, StrictUndefined

    env = Environment(undefined=StrictUndefined)
    template = env.from_string(text)
    return template.render(**variables)


def _builtin_template_root() -> Traversable:
    return resources.files("folio").joinpath("templates").joinpath("starter")


def _copy_template(source_dir: Traversable, target_dir: Path, variables: dict[str, str]) -> None:
    for child in sorted(source_dir.iterdir(), key=lambda entry: entry.name):
        if child.name in IGNORED_TEMPLATE_FILES:
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


def create_command(
    target_dir: Annotated[
        Path,
        typer.Argument(help="Path to the new project directory", exists=False),
    ],
    var: Annotated[
        list[str] | None,
        typer.Option("--var", help="Template variables as key=value pairs"),
    ] = None,
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

    try:
        target_dir.mkdir(parents=True, exist_ok=True)
        _copy_template(starter_template, target_dir, variables)
    except typer.Exit:
        raise
    except Exception as exc:
        console.print(f"[red]Create error:[/red] {exc}")
        raise typer.Exit(1) from exc

    console.print(f"Done! Starter project created in [cyan]{target_dir}[/cyan]")
