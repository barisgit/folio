from __future__ import annotations

import tempfile
from dataclasses import dataclass
from enum import StrEnum
from pathlib import Path
from typing import Protocol

from folio.dsl.model import Document, ExportFormat, ExportPreset, ExportScope, Page
from folio.dsl.renderer import (
    BuildResult,
    RenderedDocument,
    RenderedPage,
    RenderError,
    default_export_names,
    export_preset_map,
    export_preset_source_name,
    resolve_export_targets,
    write_pages,
)
from folio.export.idml import write_idml
from folio.export.pdf import PdfExportError, PdfPage, write_pdf
from folio.preview import _render_svg_preview


class ArtifactKind(StrEnum):
    """Typed built-in export artifact kinds."""

    DOCUMENT_TREE = "document-tree"
    PAGE_SVG = "page-svg"
    PAGE_PNG = "page-png"
    DOCUMENT_PDF = "document-pdf"
    DOCUMENT_IDML = "document-idml"


@dataclass(frozen=True)
class PlannedArtifact:
    """Artifact produced or consumed by an export pipeline step."""

    preset_name: str
    kind: ArtifactKind
    scope: ExportScope
    public: bool


@dataclass(frozen=True)
class PlannedStep:
    """One topologically ordered built-in export step."""

    preset: ExportPreset
    artifact: PlannedArtifact
    dependencies: tuple[PlannedArtifact, ...] = ()


@dataclass(frozen=True)
class ExportPlan:
    """Resolved export plan for one rendered document."""

    document: Document
    requested_targets: tuple[ExportPreset, ...]
    public_names: frozenset[str]
    steps: tuple[PlannedStep, ...]


@dataclass(frozen=True)
class PagePngArtifact:
    page_number: int
    path: Path


class _RenderSvg(Protocol):
    def __call__(self, svg_text: str, *, output_path: Path) -> Path: ...


def artifact_kind_for_preset(preset: ExportPreset) -> ArtifactKind:
    if preset.format is ExportFormat.SVG:
        return ArtifactKind.PAGE_SVG
    if preset.format is ExportFormat.PNG:
        return ArtifactKind.PAGE_PNG
    if preset.format is ExportFormat.PDF:
        return ArtifactKind.DOCUMENT_PDF
    if preset.format is ExportFormat.IDML:
        return ArtifactKind.DOCUMENT_IDML
    raise RenderError(f"Unsupported export preset format: {preset.format}")


def plan_export_targets(document: Document, requested: tuple[str, ...]) -> ExportPlan:
    """Resolve requested targets and dependencies for one document."""
    targets = resolve_export_targets(document, requested)
    public_names = frozenset(preset.name for preset in targets)
    presets = export_preset_map(document)
    steps: list[PlannedStep] = []
    planned: set[str] = set()
    visiting: set[str] = set()
    path: list[str] = []

    def plan_name(name: str) -> None:
        if name in planned:
            return
        if name in visiting:
            start = path.index(name)
            cycle = " -> ".join([*path[start:], name])
            raise RenderError(f"Export preset dependency cycle: {cycle}")
        preset = presets.get(name)
        if preset is None:
            raise RenderError(f"Unknown export target dependency: {name}")

        visiting.add(name)
        path.append(name)
        dependencies: list[PlannedArtifact] = []
        source_name = export_preset_source_name(preset)
        if source_name is not None:
            plan_name(source_name)
            source = presets[source_name]
            dependencies.append(
                PlannedArtifact(
                    preset_name=source.name,
                    kind=artifact_kind_for_preset(source),
                    scope=source.scope,
                    public=source.name in public_names,
                )
            )
        path.pop()
        visiting.remove(name)

        artifact = PlannedArtifact(
            preset_name=preset.name,
            kind=artifact_kind_for_preset(preset),
            scope=preset.scope,
            public=preset.name in public_names,
        )
        steps.append(
            PlannedStep(
                preset=preset,
                artifact=artifact,
                dependencies=tuple(dependencies),
            )
        )
        planned.add(name)

    for target in targets:
        plan_name(target.name)

    return ExportPlan(
        document=document,
        requested_targets=targets,
        public_names=public_names,
        steps=tuple(steps),
    )


def execute_export_plan(
    rendered_document: RenderedDocument,
    plan: ExportPlan,
    out_dir: Path,
) -> list[Path]:
    """Execute a built-in export plan for one rendered document."""
    written: list[Path] = []
    page_model_by_number = _page_by_number(rendered_document.document)
    page_pngs: dict[str, tuple[PagePngArtifact, ...]] = {}

    with tempfile.TemporaryDirectory(prefix="folio-pipeline-") as tmp_dir:
        tmp_path = Path(tmp_dir)
        for step in plan.steps:
            preset = step.preset
            public = step.artifact.public
            if step.artifact.kind is ArtifactKind.PAGE_SVG:
                if public:
                    target_result = _result_for_pages(
                        rendered_document,
                        _participating_pages(rendered_document, preset, plan=plan),
                    )
                    written.extend(write_pages(target_result, out_dir))
                continue

            if step.artifact.kind is ArtifactKind.PAGE_PNG:
                pages = _participating_pages(rendered_document, preset, plan=plan)
                pngs: list[PagePngArtifact] = []
                for page in pages:
                    output_path = (
                        out_dir / _png_output_name(page, preset)
                        if public
                        else tmp_path / f"{Path(page.filename).stem}_{preset.name}.png"
                    )
                    path = _render_svg_preview(
                        page.content,
                        output_path=output_path,
                        viewport=preset.viewport,
                    )
                    pngs.append(PagePngArtifact(page_number=page.page_number, path=path))
                    if public:
                        written.append(path)
                page_pngs[preset.name] = tuple(pngs)
                continue

            if step.artifact.kind is ArtifactKind.DOCUMENT_IDML:
                if public:
                    written.append(
                        write_idml(
                            rendered_document.document,
                            out_dir,
                            package_name=_document_artifact_name(
                                rendered_document.document, preset
                            ),
                        )
                    )
                continue

            if step.artifact.kind is ArtifactKind.DOCUMENT_PDF:
                if not public:
                    continue
                source_name = export_preset_source_name(preset)
                try:
                    if source_name is None:
                        written.append(
                            _write_legacy_pdf(
                                rendered_document,
                                preset,
                                out_dir,
                                page_model_by_number,
                            )
                        )
                    else:
                        source_pngs = page_pngs.get(source_name)
                        if source_pngs is None:
                            raise RenderError(
                                f"PDF target {preset.name} missing planned dependency: "
                                f"{source_name}"
                            )
                        written.append(
                            write_pdf(
                                rendered_document.document,
                                out_dir,
                                filename=_document_artifact_name(
                                    rendered_document.document, preset
                                ),
                                pages=tuple(
                                    PdfPage(
                                        page_number=png.page_number,
                                        svg_text=None,
                                        width_mm=page_model_by_number[png.page_number].width_mm,
                                        height_mm=page_model_by_number[png.page_number].height_mm,
                                        png_path=png.path,
                                    )
                                    for png in source_pngs
                                ),
                            )
                        )
                except PdfExportError as exc:
                    raise RenderError(f"PDF target {preset.name} failed: {exc}") from exc
                continue

            raise RenderError(f"Unsupported export pipeline artifact: {step.artifact.kind}")

    return written


def _page_by_number(document: Document) -> dict[int, Page]:
    return {page.page_number: page for page in document.pages}


def _participating_pages(
    rendered_document: RenderedDocument,
    preset: ExportPreset,
    *,
    plan: ExportPlan,
) -> list[RenderedPage]:
    page_models = _page_by_number(rendered_document.document)
    if preset.name not in plan.public_names:
        return list(rendered_document.pages)
    defaults = default_export_names(rendered_document.document)
    if preset.name in defaults or preset.format is ExportFormat.SVG:
        return list(rendered_document.pages)
    return [
        page
        for page in rendered_document.pages
        if preset.name in page_models[page.page_number].extra_exports
    ]


def _result_for_pages(
    rendered_document: RenderedDocument, pages: list[RenderedPage]
) -> BuildResult:
    selected_numbers = {page.page_number for page in pages}
    selected_document = rendered_document.document
    if selected_numbers:
        selected_document = Document(
            pages=tuple(
                page
                for page in rendered_document.document.pages
                if page.page_number in selected_numbers
            ),
            defs=rendered_document.document.defs,
            config_hash=rendered_document.document.config_hash,
            metadata=rendered_document.document.metadata,
            document_id=rendered_document.document.document_id,
            filename=rendered_document.document.filename,
            title=rendered_document.document.title,
            export_presets=rendered_document.document.export_presets,
            default_exports=rendered_document.document.default_exports,
        )
    selected = RenderedDocument(document=selected_document, pages=pages)
    return BuildResult(pages=pages, config_hash="", documents=[selected])


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


def _write_legacy_pdf(
    rendered_document: RenderedDocument,
    preset: ExportPreset,
    out_dir: Path,
    page_model_by_number: dict[int, Page],
) -> Path:
    pdf_pages = tuple(
        PdfPage(
            page_number=page.page_number,
            svg_text=page.content,
            width_mm=page_model_by_number[page.page_number].width_mm,
            height_mm=page_model_by_number[page.page_number].height_mm,
        )
        for page in rendered_document.pages
    )
    return write_pdf(
        rendered_document.document,
        out_dir,
        filename=_document_artifact_name(rendered_document.document, preset),
        pages=pdf_pages,
        render_svg=lambda svg_text, output_path: _render_svg_preview(
            svg_text, output_path=output_path
        ),
    )
