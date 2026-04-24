"""Folio CLI — thin IO adapters, zero business logic.

Every command in this package is a pure adapter that:
1. Parses CLI arguments (Typer annotations)
2. Delegates to the engine
3. Formats output (Rich console)

No business logic lives here.
"""
from __future__ import annotations

import importlib.metadata

import typer
from rich.console import Console

from folio.cli.build import build_command
from folio.cli.check import check_command
from folio.cli.create import create_command
from folio.cli.docs import docs_app
from folio.cli.rasterize import rasterize_command
from folio.cli.reconcile import reconcile_command
from folio.cli.skill import skill_app
from folio.cli.validate import validate_command
from folio.cli.search import search_app

__all__: list[str] = []

console = Console()

app = typer.Typer(
    name="folio",
    help="Create, check, build, rasterize, validate, and reconcile page SVGs.",
    no_args_is_help=True,
    rich_markup_mode="rich",
    context_settings={"help_option_names": ["-h", "--help"]},
    pretty_exceptions_enable=True,
    pretty_exceptions_show_locals=False,
)


def version_callback(value: bool) -> None:
    if value:
        console.print(importlib.metadata.version("folio"))
        raise typer.Exit()


@app.callback()
def main(
    version: bool | None = typer.Option(
        None,
        "--version",
        "-V",
        callback=version_callback,
        is_eager=True,
        help="Show version and exit.",
    ),
) -> None:
    _ = version


app.command("build")(build_command)
app.command("create")(create_command)
app.command("validate")(validate_command)
app.command("rasterize")(rasterize_command)
app.command("reconcile")(reconcile_command)
app.command("check")(check_command)
app.add_typer(search_app, name="search")
app.add_typer(docs_app, name="docs")
app.add_typer(skill_app, name="skill")
