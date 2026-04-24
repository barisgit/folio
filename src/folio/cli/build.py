"""`folio build` command — thin IO adapter."""

from __future__ import annotations

from pathlib import Path
from typing import Annotated

import typer
from rich.console import Console

from folio.core.cache import cache_build
from folio.core.dsl.loader import DslError, load_dsl_module, resolve_spec_path
from folio.core.export.pipeline import execute_export_plan, plan_export_targets
from folio.core.export.targets import (
    document_requested_targets,
    filter_result_by_page,
    reject_page_with_document_targets,
    reject_unknown_collection_targets,
)
from folio.core.render.pipeline import (
    RenderError,
    collection_from_module,
    render_collection,
)

console = Console()


def _looks_like_spec_path(value: str) -> bool:
    path = Path(value).expanduser()
    return path.exists() or path.suffix == ".py" or "/" in value


def _split_spec_and_targets(args: list[str] | None) -> tuple[Path | None, tuple[str, ...]]:
    values = list(args or [])
    if not values:
        return None, ()
    if _looks_like_spec_path(values[0]):
        return Path(values[0]), tuple(values[1:])
    return None, tuple(values)


def build_command(
    args: Annotated[
        list[str] | None,
        typer.Argument(help="Optional spec path followed by export targets"),
    ] = None,
    out_dir: Annotated[
        Path | None, typer.Option("--out-dir", help="Directory for rendered output")
    ] = None,
    page_number: Annotated[
        int | None,
        typer.Option("--page", min=1, help="Only write a single page number"),
    ] = None,
    no_cache: Annotated[
        bool,
        typer.Option("--no-cache", help="Skip updating the last-build cache"),
    ] = False,
) -> None:
    spec_path, requested_targets = _split_spec_and_targets(args)
    resolved_spec = resolve_spec_path(spec_path)
    resolved_out_dir = (out_dir or (resolved_spec.parent / "out")).expanduser().resolve()
    try:
        dsl_module = load_dsl_module(resolved_spec)
        collection = collection_from_module(dsl_module)
        result = render_collection(
            collection,
            config_dir=resolved_spec.parent,
            source_path=resolved_spec,
        )
        reject_unknown_collection_targets(
            tuple(rd.document for rd in result.documents),
            requested_targets,
        )
        requested_plans = tuple(
            plan_export_targets(
                rd.document,
                document_requested_targets(rd.document, requested_targets),
            )
            for rd in result.documents
            if document_requested_targets(rd.document, requested_targets)
            or not requested_targets
            or tuple(requested_targets) == ("all",)
            or "all" in requested_targets
        )
        all_targets = tuple(target for plan in requested_plans for target in plan.requested_targets)
        reject_page_with_document_targets(all_targets, page_number)
        output_result = filter_result_by_page(result, page_number)

        written: list[Path] = []
        for rendered_document in output_result.documents:
            document_targets = document_requested_targets(
                rendered_document.document, requested_targets
            )
            if requested_targets and document_targets == ():
                continue
            plan = plan_export_targets(rendered_document.document, document_targets)
            written.extend(execute_export_plan(rendered_document, plan, resolved_out_dir))
        cached = None if no_cache else cache_build(result, spec_path=resolved_spec)
    except DslError as exc:
        console.print(f"[red]Build error:[/red] {exc}")
        raise typer.Exit(1) from exc
    except RenderError as exc:
        console.print(f"[red]Render error:[/red] {exc}")
        raise typer.Exit(2) from exc

    for path in written:
        console.print(f"wrote [green]{path}[/green]")
    if cached is not None:
        console.print(f"cached build in [cyan]{cached.manifest.parent}[/cyan]")
