from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from folio.core.render.primitives import pt_to_mm
from folio.services.reconcile.parse import ParsedElement, ParsedSvg


@dataclass(frozen=True)
class DiffResult:
    page_number: int | None
    changes: list[dict[str, Any]]
    warnings: list[dict[str, Any]]


_NUMERIC_ATTRS = {"cx", "cy", "font-size", "height", "r", "width", "x", "x1", "x2", "y", "y1", "y2"}
_IGNORED_ATTRS = {"data-page-id", "data-page-number", "id", "label"}


class DiffError(Exception):
    """Raised when two SVG trees cannot be compared."""


def _float_or_none(value: str | None) -> float | None:
    if value is None:
        return None
    try:
        return float(value)
    except ValueError:
        return None


def _numeric_change(attr: str, old: str, new: str) -> dict[str, Any]:
    old_float = _float_or_none(old)
    new_float = _float_or_none(new)
    if attr == "font-size":
        return {"font_size_pt": {"from": old_float, "to": new_float}}

    key = attr.replace("-", "_")
    return {
        f"{key}_pt": {"from": old_float, "to": new_float},
        f"{key}_mm": {
            "from": pt_to_mm(old_float) if old_float is not None else None,
            "to": pt_to_mm(new_float) if new_float is not None else None,
        },
    }


def _element_changes(base: ParsedElement, edited: ParsedElement) -> dict[str, Any] | None:
    attrs: dict[str, Any] = {}

    if base.text != edited.text:
        attrs["text"] = {"from": base.text, "to": edited.text}

    for attr in sorted((set(base.attrs) | set(edited.attrs)) - _IGNORED_ATTRS):
        old = base.attrs.get(attr)
        new = edited.attrs.get(attr)
        if old == new:
            continue
        if attr in _NUMERIC_ATTRS and old is not None and new is not None:
            attrs.update(_numeric_change(attr, old, new))
            continue
        key = attr.replace("-", "_")
        attrs[key] = {"from": old, "to": new}

    if not attrs:
        return None
    return {"id": base.element_id, "kind": "attribute", "attrs": attrs}


def diff_svgs(base: ParsedSvg, edited: ParsedSvg) -> DiffResult:
    page_number = edited.page_number or base.page_number
    changes: list[dict[str, Any]] = []
    warnings: list[dict[str, Any]] = []

    shared_ids = sorted(set(base.elements) & set(edited.elements))
    for element_id in shared_ids:
        change = _element_changes(base.elements[element_id], edited.elements[element_id])
        if change is not None:
            changes.append(change)

    for element_id in sorted(set(edited.elements) - set(base.elements)):
        element = edited.elements[element_id]
        warnings.append(
            {
                "kind": "added_element",
                "id": element_id,
                "tag": element.tag,
                "parent_id": element.parent_id,
            }
        )

    for element_id in sorted(set(base.elements) - set(edited.elements)):
        warnings.append({"kind": "deleted_element", "id": element_id})

    return DiffResult(page_number=page_number, changes=changes, warnings=warnings)
