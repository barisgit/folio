"""`folio check` command — thin IO adapter."""
from __future__ import annotations

from pathlib import Path
from typing import Annotated

import typer

from folio.services.check.runner import CheckResult, run_check
from folio.services.check.target import resolve_check_target


def _format_summary(*, verbose: bool, result: CheckResult) -> str:
    lines: list[str] = []
    for step in result.steps:
        status = "✓" if step.success else "✗"
        label = step.label
        if step.backend_name:
            label = f"{label} ({step.backend_name})"
        lines.append(f"{status} {label}")

        if verbose and step.command:
            lines.append(f"    $ {' '.join(step.command)}")
        if verbose and step.skipped_backends:
            lines.append(f"    skipped: {', '.join(step.skipped_backends)}")
        if step.output:
            for line in step.output.splitlines():
                lines.append(f"    {line}")
    return "\n".join(lines)


def check_command(
    target: Annotated[
        Path | None,
        typer.Argument(help="Project directory or spec file. Defaults to cwd/build.py."),
    ] = None,
    format: Annotated[
        bool,
        typer.Option("--format", help="Also check formatting."),
    ] = False,
    fix: Annotated[
        bool,
        typer.Option("--fix", help="Autofix lint/format issues (implies --format)."),
    ] = False,
    verbose: Annotated[
        bool,
        typer.Option("--verbose", "-v", help="Show selected commands and backend output."),
    ] = False,
) -> None:
    """Validate, lint, and typecheck a Folio project."""
    resolved_format = format or fix
    result = run_check(
        resolve_check_target(target),
        fmt=resolved_format,
        fix=fix,
        verbose=verbose,
    )
    output = _format_summary(verbose=verbose, result=result)
    if result.exit_code == 0:
        typer.echo(output)
        return
    typer.echo(output, err=True)
    raise typer.Exit(result.exit_code)
