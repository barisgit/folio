from __future__ import annotations

from folio.core.export.pipeline import ArtifactKind, plan_export_targets
from folio.dsl import document, page, pdf, png, rect, svg


def _document():
    return document(
        "brochure",
        pages=[
            page(rect("p1_bg", 0, 0, 10, 10), page_id="p1", filename="p1.svg", page_number=1),
            page(rect("p2_bg", 0, 0, 10, 10), page_id="p2", filename="p2.svg", page_number=2),
        ],
        export_presets=[
            svg(),
            png("1080p", viewport=(1920, 1080)),
            png("thumb", viewport=(320, 180)),
            pdf(source="1080p"),
        ],
        default_exports=["pdf"],
    )


def test_plan_export_targets_includes_transitive_dependencies() -> None:
    plan = plan_export_targets(_document(), ("pdf",))

    assert [step.preset.name for step in plan.steps] == ["svg", "1080p", "pdf"]
    assert [step.artifact.kind for step in plan.steps] == [
        ArtifactKind.PAGE_SVG,
        ArtifactKind.PAGE_PNG,
        ArtifactKind.DOCUMENT_PDF,
    ]
    assert [step.artifact.public for step in plan.steps] == [False, False, True]


def test_plan_export_targets_reuses_shared_dependencies() -> None:
    plan = plan_export_targets(_document(), ("1080p", "pdf"))

    assert [step.preset.name for step in plan.steps] == ["svg", "1080p", "pdf"]
    assert [step.artifact.public for step in plan.steps] == [False, True, True]


def test_plan_export_targets_all_makes_declared_presets_public() -> None:
    plan = plan_export_targets(_document(), ("all",))

    assert [step.preset.name for step in plan.steps] == ["svg", "1080p", "thumb", "pdf"]
    assert all(step.artifact.public for step in plan.steps)
