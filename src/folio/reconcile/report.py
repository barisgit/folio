from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from rich.console import Console

from folio.reconcile.diff import DiffResult

console = Console()


def _warning_buckets(
    warnings: list[dict[str, Any]],
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    added = [warning for warning in warnings if warning.get("kind") == "added_element"]
    removed = [warning for warning in warnings if warning.get("kind") == "deleted_element"]
    return added, removed


def report_payload(
    *,
    result: DiffResult,
    base_svg: Path,
    edited_svg: Path,
    page_id: str | None = None,
) -> dict[str, Any]:
    unmatched_added, unmatched_removed = _warning_buckets(result.warnings)
    return {
        "page_number": result.page_number,
        "page_id": page_id,
        "base_svg": str(base_svg),
        "edited_svg": str(edited_svg),
        "changes": result.changes,
        "unmatched_added": unmatched_added,
        "unmatched_removed": unmatched_removed,
        "warnings": result.warnings,
    }


def write_report(path: Path, payload: dict[str, Any]) -> None:
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")


def print_report(payload: dict[str, Any]) -> None:
    warnings = payload.get("warnings")
    if warnings is None:
        warnings = payload.get("unmatched_added", []) + payload.get("unmatched_removed", [])
    change_count = len(payload["changes"])
    warning_count = len(warnings)
    console.print(f"Page: [cyan]{payload.get('page_id') or payload.get('page_number')}[/cyan]")
    console.print(f"Base: [dim]{payload['base_svg']}[/dim]")
    console.print(f"Edited: [dim]{payload['edited_svg']}[/dim]")
    console.print(f"Changes: [bold]{change_count}[/bold], warnings: [bold]{warning_count}[/bold]")

    for change in payload["changes"]:
        console.print(f"\n[bold yellow]{change['id']}[/bold yellow]")
        for attr, value in change["attrs"].items():
            console.print(f"  - {attr}: {value['from']} -> {value['to']}")

    for warning in warnings:
        if warning["kind"] == "added_element":
            console.print(
                f"\n[red]warning[/red] added {warning['tag']} "
                f"id={warning.get('id')} parent={warning.get('parent_id')}"
            )
        else:
            console.print(f"\n[red]warning[/red] deleted id={warning.get('id')}")
