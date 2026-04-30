"""`folio dev` command — local tweak playground server."""

from __future__ import annotations

import webbrowser
from pathlib import Path
from typing import Annotated

import typer
from rich.console import Console

from folio.core.dsl.loader import DslError, resolve_spec_path
from folio.core.dsl.tweak_values import TweakValuesError
from folio.core.render.pipeline import RenderError
from folio.services.playground import PlaygroundUpdateError
from folio.services.playground_server import create_playground_server, playground_url
from folio.services.tweaks_load import TweakValidationError

console = Console()


def dev_command(
    spec_path: Annotated[Path | None, typer.Argument(help="Path to Python DSL module")] = None,
    host: Annotated[str, typer.Option("--host", help="Host/interface to bind")] = "127.0.0.1",
    port: Annotated[int, typer.Option("--port", min=0, help="Port to bind (0 picks a free port)")] = 0,
    open_browser: Annotated[
        bool,
        typer.Option("--open/--no-open", help="Open the playground in the default browser"),
    ] = False,
) -> None:
    """Serve the local browser playground for declared tweak values."""

    try:
        resolved_spec = resolve_spec_path(spec_path)
        server = create_playground_server(resolved_spec, host=host, port=port)
    except TweakValuesError as exc:
        console.print(f"[red]Dev server error:[/red] {exc}")
        raise typer.Exit(1) from exc
    except TweakValidationError as exc:
        for diagnostic in exc.diagnostics:
            console.print(f"[red]Tweak error[/red] {diagnostic.key}: {diagnostic.message}")
        raise typer.Exit(1) from exc
    except (DslError, RenderError, PlaygroundUpdateError, OSError) as exc:
        console.print(f"[red]Dev server error:[/red] {exc}")
        raise typer.Exit(1) from exc

    url = playground_url(server)
    console.print(f"Serving Folio playground at {url}")
    if open_browser:
        try:
            webbrowser.open(url)
        except Exception:
            # Browser launch is a convenience only; serving still succeeds.
            pass

    try:
        server.serve_forever()
    except KeyboardInterrupt:
        console.print("\nStopping Folio playground.")
    finally:
        server.server_close()
