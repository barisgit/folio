from __future__ import annotations

from dataclasses import replace
from pathlib import Path
from typing import Annotated

import typer
from rich.console import Console

from folio.cache import cache_build
from folio.dsl.loader import DslError, load_dsl_module, resolve_spec_path
from folio.dsl.model import Document, ExportFormat, ExportPreset, ExportScope, Page
from folio.dsl.renderer import (
    BuildResult,
    RenderedDocument,
    RenderedPage,
    RenderError,
    collection_from_module,
    default_export_names,
    render_collection,
    resolve_export_targets,
    write_pages,
)
from folio.export import write_idml, write_pdf
from folio.preview import _render_svg_preview

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


def _page_by_number(document: Document) -> dict[int, Page]:
    return {page.page_number: page for page in document.pages}


def _participating_pages(
    rendered_document: RenderedDocument,
    preset: ExportPreset,
    *,
    default_names: tuple[str, ...],
) -> list[RenderedPage]:
    pages_by_number = _page_by_number(rendered_document.document)
    if preset.name in default_names or preset.format is ExportFormat.SVG:
        return list(rendered_document.pages)
    return [
        page
        for page in rendered_document.pages
        if preset.name in pages_by_number[page.page_number].extra_exports
    ]


def _build_result_for_pages(
    result: BuildResult,
    preset: ExportPreset,
    *,
    default_names: tuple[str, ...],
) -> BuildResult:
    selected_documents: list[RenderedDocument] = []
    selected_pages: list[RenderedPage] = []
    for rendered_document in result.documents:
        rendered_pages = _participating_pages(
            rendered_document,
            preset,
            default_names=default_names,
        )
        if not rendered_pages:
            continue
        selected_page_numbers = {page.page_number for page in rendered_pages}
        selected_document_pages = tuple(
            page
            for page in rendered_document.document.pages
            if page.page_number in selected_page_numbers
        )
        selected_document = replace(rendered_document.document, pages=selected_document_pages)
        selected_documents.append(
            RenderedDocument(document=selected_document, pages=rendered_pages)
        )
        selected_pages.extend(rendered_pages)
    return BuildResult(
        pages=selected_pages,
        config_hash=result.config_hash,
        documents=selected_documents,
    )


def _png_output_name(page: RenderedPage, preset: ExportPreset) -> str:
    stem = Path(page.filename).stem
    if preset.filename_pattern:
        return preset.filename_pattern.format(
            stem=stem,
            preset=preset.name,
            page_id=page.page_id,
            page_number=page.page_number,
        )
    return f"{stem}_{preset.name}.png"


def _document_artifact_name(document: Document, preset: ExportPreset) -> str:
    extension = preset.format.value
    base = document.filename or document.document_id or "folio"
    if preset.filename_pattern:
        return preset.filename_pattern.format(
            stem=base,
            preset=preset.name,
            document_id=document.document_id,
        )
    return f"{base}.{extension}"


def _write_pngs(result: BuildResult, preset: ExportPreset, out_dir: Path) -> list[Path]:
    written: list[Path] = []
    for page in result.pages:
        target = out_dir / _png_output_name(page, preset)
        written.append(
            _render_svg_preview(
                page.content,
                output_path=target,
                viewport=preset.viewport,
            )
        )
    return written


def _write_document_export(
    rendered_document: RenderedDocument,
    preset: ExportPreset,
    out_dir: Path,
) -> Path:
    artifact_name = _document_artifact_name(rendered_document.document, preset)
    if preset.format is ExportFormat.IDML:
        return write_idml(rendered_document.document, out_dir, package_name=artifact_name)
    if preset.format is ExportFormat.PDF:
        return write_pdf(rendered_document.document, out_dir, filename=artifact_name)
    raise RenderError(f"Unsupported document export format: {preset.format}")


def _write_target(
    result: BuildResult,
    preset: ExportPreset,
    out_dir: Path,
    *,
    default_names: tuple[str, ...],
) -> list[Path]:
    if preset.scope is ExportScope.DOCUMENT:
        return [
            _write_document_export(rendered_document, preset, out_dir)
            for rendered_document in result.documents
        ]

    target_result = _build_result_for_pages(
        result,
        preset,
        default_names=default_names,
    )
    if preset.format is ExportFormat.SVG:
        return write_pages(target_result, out_dir)
    if preset.format is ExportFormat.PNG:
        return _write_pngs(target_result, preset, out_dir)
    raise RenderError(f"Unsupported page export format: {preset.format}")


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
        requested_by_document = tuple(
            (
                rendered_document,
                resolve_export_targets(rendered_document.document, requested_targets),
            )
            for rendered_document in result.documents
        )
        all_targets = tuple(
            target
            for _, targets in requested_by_document
            for target in targets
        )
        _reject_page_with_document_targets(all_targets, page_number)
        output_result = _filter_result_by_page(result, page_number)

        written: list[Path] = []
        for rendered_document in output_result.documents:
            document_result = BuildResult(
                pages=list(rendered_document.pages),
                config_hash=output_result.config_hash,
                documents=[rendered_document],
            )
            default_names = default_export_names(rendered_document.document)
            targets = resolve_export_targets(rendered_document.document, requested_targets)
            for target in targets:
                written.extend(
                    _write_target(
                        document_result,
                        target,
                        resolved_out_dir,
                        default_names=default_names,
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
