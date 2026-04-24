from __future__ import annotations

from dataclasses import replace
from pathlib import Path
from typing import Annotated

import typer
from rich.console import Console

from folio.cache import cache_build
from folio.dsl.loader import DslError, load_dsl_module, resolve_spec_path
from folio.dsl.model import ExportPreset, ExportScope
from folio.dsl.renderer import (
    BuildResult,
    RenderedDocument,
    RenderError,
    collection_from_module,
    render_collection,
)
from folio.export.pipeline import execute_export_plan, plan_export_targets

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


def _filter_result_by_page(result: BuildResult, page_number: int | None) -> BuildResult:
    if page_number is None:
        return result

    selected_documents: list[RenderedDocument] = []
    selected_pages = []
    for rendered_document in result.documents:
        document_pages = [
            page for page in rendered_document.document.pages if page.page_number == page_number
        ]
        rendered_pages = [
            page for page in rendered_document.pages if page.page_number == page_number
        ]
        if not document_pages:
            continue
        selected_document = replace(rendered_document.document, pages=tuple(document_pages))
        selected_documents.append(
            RenderedDocument(document=selected_document, pages=rendered_pages)
        )
        selected_pages.extend(rendered_pages)

    if not selected_pages:
        raise RenderError(f"Page {page_number} not found in spec")
    return BuildResult(
        pages=selected_pages,
        config_hash=result.config_hash,
        documents=selected_documents,
    )



def _reject_page_with_document_targets(
    targets: tuple[ExportPreset, ...], page_number: int | None
) -> None:
    if page_number is None:
        return
    document_targets = [target.name for target in targets if target.scope is ExportScope.DOCUMENT]
    if document_targets:
        joined = ", ".join(document_targets)
        raise RenderError(f"--page applies only to page-scoped export targets: {joined}")


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
        requested_plans = tuple(
            plan_export_targets(rendered_document.document, requested_targets)
            for rendered_document in result.documents
        )
        all_targets = tuple(
            target for plan in requested_plans for target in plan.requested_targets
        )
        _reject_page_with_document_targets(all_targets, page_number)
        output_result = _filter_result_by_page(result, page_number)

        written: list[Path] = []
        for rendered_document in output_result.documents:
            plan = plan_export_targets(rendered_document.document, requested_targets)
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
