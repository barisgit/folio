from __future__ import annotations

from pathlib import Path
from typing import Annotated

import typer
from rich.console import Console

from folio.dsl.loader import DslError, load_dsl_module, resolve_spec_path
from folio.dsl.renderer import RenderError, document_from_module, validate_document

console = Console()


def validate_command(
    spec_path: Annotated[Path | None, typer.Argument(help="Path to Python DSL module")] = None,
) -> None:
    resolved_spec = resolve_spec_path(spec_path)
    try:
        module = load_dsl_module(resolved_spec)
        validate_document(document_from_module(module))
    except (DslError, RenderError) as exc:
        console.print(f"[red]Validation error:[/red] {exc}")
        raise typer.Exit(1) from exc

    console.print(f"[green]valid[/green] {resolved_spec}")
