from __future__ import annotations

from dataclasses import replace
from enum import StrEnum
from pathlib import Path
from typing import Annotated

import typer
from rich.console import Console

from folio.cache import cache_build
from folio.dsl.loader import DslError, load_dsl_module, resolve_spec_path
from folio.dsl.renderer import (
    BuildResult,
    RenderedDocument,
    RenderError,
    collection_from_module,
    render_collection,
    write_pages,
)
from folio.export import write_idml

console = Console()


class BuildFormat(StrEnum):
    SVG = "svg"
    IDML = "idml"


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


def _idml_package_name(rendered_document: RenderedDocument) -> str:
    document = rendered_document.document
    base = document.filename or document.document_id or "folio"
    return f"{base}.idml"


def build_command(
    spec_path: Annotated[Path | None, typer.Argument(help="Path to Python DSL module")] = None,
    out_dir: Annotated[
        Path | None, typer.Option("--out-dir", help="Directory for rendered output")
    ] = None,
    output_format: Annotated[
        BuildFormat,
        typer.Option("--format", help="Output format: svg or idml"),
    ] = BuildFormat.SVG,
    page_number: Annotated[
        int | None,
        typer.Option("--page", min=1, help="Only write a single page number"),
    ] = None,
    no_cache: Annotated[
        bool,
        typer.Option("--no-cache", help="Skip updating the last-build cache"),
    ] = False,
) -> None:
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
        output_result = _filter_result_by_page(result, page_number)
        written = write_pages(output_result, resolved_out_dir)
        if output_format is BuildFormat.IDML:
            for rendered_document in output_result.documents:
                written.append(
                    write_idml(
                        rendered_document.document,
                        resolved_out_dir,
                        package_name=_idml_package_name(rendered_document),
                    )
                )
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
