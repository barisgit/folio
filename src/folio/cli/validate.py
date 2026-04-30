"""`folio validate` command — thin IO adapter."""

from __future__ import annotations

from pathlib import Path
from typing import Annotated

import typer
from rich.console import Console

from folio.core.dsl.loader import DslError, resolve_spec_path
from folio.core.dsl.tweak_values import TweakValuesError
from folio.core.render.pipeline import RenderError
from folio.services.tweaks_load import (
    TweakValidationError,
    validate_spec_with_tweaks,
)

console = Console()


def validate_command(
    spec_path: Annotated[Path | None, typer.Argument(help="Path to Python DSL module")] = None,
) -> None:
    resolved_spec = resolve_spec_path(spec_path)
    try:
        outcome = validate_spec_with_tweaks(resolved_spec)
    except TweakValuesError as exc:
        console.print(f"[red]Validation error:[/red] {exc}")
        raise typer.Exit(1) from exc
    except TweakValidationError as exc:
        for diagnostic in exc.diagnostics:
            console.print(f"[red]Tweak error[/red] {diagnostic.key}: {diagnostic.message}")
        raise typer.Exit(1) from exc
    except (DslError, RenderError) as exc:
        console.print(f"[red]Validation error:[/red] {exc}")
        raise typer.Exit(1) from exc

    for diagnostic in outcome.diagnostics:
        if diagnostic.severity == "warning":
            console.print(f"[yellow]Tweak warning[/yellow] {diagnostic.key}: {diagnostic.message}")

    console.print(f"[green]valid[/green] {resolved_spec}")
