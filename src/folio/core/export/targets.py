"""Export target resolution — extracted from CLI build command.

Determines which export targets apply to a given document and validates
user-requested targets against what the collection actually provides.
"""

from __future__ import annotations

from dataclasses import replace

from folio.core.model import Document, ExportPreset, ExportScope
from folio.core.model.result import BuildResult, RenderedDocument, RenderError
from folio.core.render.pipeline import export_preset_map


def document_requested_targets(document: Document, requested: tuple[str, ...]) -> tuple[str, ...]:
    """Return the subset of *requested* target names valid for *document*."""
    if not requested or tuple(requested) == ("all",) or "all" in requested:
        return requested
    presets = export_preset_map(document)
    return tuple(name for name in requested if name in presets)


def filter_result_by_page(result: BuildResult, page_number: int | None) -> BuildResult:
    """Return a new BuildResult containing only *page_number*."""
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


def reject_unknown_collection_targets(
    documents: tuple[Document, ...], requested: tuple[str, ...]
) -> None:
    """Raise RenderError if *requested* contains names not in any document's presets."""
    if not requested or tuple(requested) == ("all",) or "all" in requested:
        return
    known = set().union(*(export_preset_map(document) for document in documents))
    missing = tuple(name for name in requested if name not in known)
    if missing:
        joined = ", ".join(missing)
        raise RenderError(f"Unknown export target: {joined}")


def reject_page_with_document_targets(
    targets: tuple[ExportPreset, ...], page_number: int | None
) -> None:
    """Raise RenderError if --page is used with document-scoped targets."""
    if page_number is None:
        return
    document_targets = [target.name for target in targets if target.scope is ExportScope.DOCUMENT]
    if document_targets:
        joined = ", ".join(document_targets)
        raise RenderError(f"--page applies only to page-scoped export targets: {joined}")
