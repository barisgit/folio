"""`folio reconcile` command — thin IO adapter."""
from __future__ import annotations

import json
from pathlib import Path
from typing import Annotated, Any

import typer
from rich.console import Console

from folio.core.cache import CacheError, cached_pages, last_build_svg, reconcile_report_path
from folio.services.reconcile.diff import diff_svgs
from folio.services.reconcile.parse import ParsedSvg, ParseError, parse_svg
from folio.services.reconcile.report import print_report, report_payload, write_report
from folio.core.dsl.loader import resolve_spec_path

console = Console()


def _page_id(parsed: ParsedSvg) -> str | None:
    for element in parsed.elements.values():
        if element.tag != "g" or element.parent_id is not None:
            continue
        page_id = element.attrs.get("data-page-id")
        if page_id:
            return page_id
    for element in parsed.elements.values():
        page_id = element.attrs.get("data-page-id")
        if page_id:
            return page_id
    return None


def _reconcile_one(
    spec_path: Path,
    edited_svg: Path,
    *,
    page_number: int | None = None,
) -> tuple[dict[str, Any], bool]:
    edited = parse_svg(edited_svg)
    resolved_page_number = page_number or edited.page_number
    if resolved_page_number is None:
        raise ParseError(f"Could not determine page number for {edited_svg}")

    base_svg = last_build_svg(spec_path, resolved_page_number)
    base = parse_svg(base_svg)
    result = diff_svgs(base, edited)
    payload = report_payload(
        result=result,
        base_svg=base_svg,
        edited_svg=edited_svg,
        page_id=_page_id(edited) or _page_id(base),
    )
    report_path = reconcile_report_path(spec_path, resolved_page_number)
    write_report(report_path, payload)
    payload["report_path"] = str(report_path)
    return payload, bool(result.changes)


def reconcile_command(
    edited_svg: Annotated[
        Path | None, typer.Argument(help="Edited SVG file to compare against cache")
    ] = None,
    all_pages: Annotated[
        bool, typer.Option("--all", help="Compare every cached page against SVGs in --edited-dir")
    ] = False,
    edited_dir: Annotated[
        Path, typer.Option("--edited-dir", help="Directory containing edited SVGs for --all mode")
    ] = Path("out"),
    page_number: Annotated[
        int | None,
        typer.Option("--page", min=1, help="Override the page number for a single edited SVG"),
    ] = None,
    spec_path: Annotated[
        Path | None, typer.Option("--spec", help="Spec file used for cache location")
    ] = None,
    output_format: Annotated[
        str, typer.Option("--format", help="Report format: text or json")
    ] = "text",
) -> None:
    resolved_spec = resolve_spec_path(spec_path)
    normalized_format = output_format.lower()
    if normalized_format not in {"text", "json"}:
        raise typer.BadParameter("--format must be one of: text, json")

    if all_pages and page_number is not None:
        raise typer.BadParameter("--page cannot be used with --all")

    try:
        payloads: list[dict[str, Any]] = []
        if all_pages:
            any_changes = False
            for page in cached_pages(resolved_spec):
                candidate = edited_dir / page.filename
                if not candidate.exists():
                    raise FileNotFoundError(
                        f"Missing edited SVG for page {page.page_number}: {candidate}"
                    )
                payload, changed = _reconcile_one(
                    resolved_spec,
                    candidate,
                    page_number=page.page_number,
                )
                payloads.append(payload)
                any_changes = changed or any_changes
        else:
            if edited_svg is None:
                raise typer.BadParameter("Provide <edited.svg> or use --all")
            payload, any_changes = _reconcile_one(
                resolved_spec,
                edited_svg,
                page_number=page_number,
            )
            payloads.append(payload)
    except typer.BadParameter:
        raise
    except (CacheError, FileNotFoundError, ParseError) as exc:
        console.print(f"[red]Reconcile error:[/red] {exc}")
        raise typer.Exit(2) from exc

    if normalized_format == "json":
        output: dict[str, Any] | list[dict[str, Any]]
        output = payloads if all_pages else payloads[0]
        console.print_json(json.dumps(output, indent=2))
    else:
        for payload in payloads:
            print_report(payload)
            console.print(f"json: [dim]{payload['report_path']}[/dim]")

    if any_changes:
        raise typer.Exit(3)
