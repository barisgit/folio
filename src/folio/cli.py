from __future__ import annotations

import importlib.metadata

import typer
from rich.console import Console

from folio.commands import (
    build_command,
    create_command,
    preview_command,
    reconcile_command,
    validate_command,
)
from folio.commands.search import search_app

console = Console()

app = typer.Typer(
    name="folio",
    help="Create, build, preview, validate, and reconcile page SVGs.",
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
app.command("preview")(preview_command)
app.command("reconcile")(reconcile_command)
app.add_typer(search_app, name="search")
