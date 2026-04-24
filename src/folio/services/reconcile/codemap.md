# src/folio/reconcile/

## Responsibility
Implements SVG reconciliation: parsing SVG files into structured intermediate representations, computing semantic diffs between two versions, and formatting results as JSON or rich console output.

## Design Patterns
- **Pipeline / Stage**: `parse_svg()` → `diff_svgs()` → `report_payload()` / `print_report()` — a clear three-stage processing pipeline.
- **Visitor / Tree Walker**: `_walk()` recursively traverses the parsed SVG tree, building a flat `dict[str, ParsedElement]` indexed by element `id`.
- **Data Transfer Object (DTO)**: Immutable `ParsedElement`, `ParsedSvg`, and `DiffResult` frozen dataclasses serve as the internal data contract between pipeline stages.
- **Namespace Stripping**: All SVG tags and attributes are stripped of namespace prefixes (e.g. `svg:rect` → `rect`) to ensure consistent comparison regardless of source tooling.

## Data & Control Flow

### Parse Stage (`parse.py`)
1. `parse_svg(Path)` is called with a file path.
2. `_SvgTreeParser` (extends `html.parser.HTMLParser`) reads the SVG text and builds an in-memory tree of `_SvgNode` objects.
3. `_walk()` traverses the tree depth-first, emitting one `ParsedElement` per element that has an `id` attribute.
4. `detect_page_number()` resolves page number from:
   - `data-page-number` attribute on a root-level `<g>` element (explicit).
   - Fallback: regex on the filename stem (e.g. `page2.svg`).
5. Returns a `ParsedSvg` containing the path, resolved page number, and the flat dict of `ParsedElement` objects.

### Diff Stage (`diff.py`)
1. `diff_svgs(ParsedSvg, ParsedSvg)` receives a `base` and `edited` parsed SVG.
2. Computes set intersection of element IDs (`shared_ids`) — these are eligible for attribute-level diffing.
3. For each shared ID, `_element_changes()` compares:
   - Text content.
   - All attributes except a hardcoded ignore set (`_IGNORED_ATTRS` = `data-page-id`, `data-page-number`, `id`, `label`).
   - Numeric attributes (`cx`, `cy`, `font-size`, `height`, `r`, `width`, `x`, `y`, etc.) are converted to both pt and mm units.
4. Set differences produce `added_element` and `deleted_element` warnings (not changes).
5. Returns `DiffResult(page_number, changes, warnings)`.

### Report Stage (`report.py`)
1. `report_payload()` packages `DiffResult` into a JSON-serializable dict with bucketed `unmatched_added` / `unmatched_removed` warnings.
2. `write_report(Path, payload)` writes that dict as indented JSON to a file.
3. `print_report(payload)` renders the diff to the terminal using `rich.Console`, printing a per-page summary, attribute-level changes, and warnings with color.

## Key Data Structures

| Class | Package | Purpose |
|---|---|---|
| `ParsedElement` | `parse.py` | Immutable record of one SVG element: id, tag, text, attrs, parent_id |
| `ParsedSvg` | `parse.py` | Immutable container: path, page_number, elements dict |
| `DiffResult` | `diff.py` | Immutable diff output: page_number, changes list, warnings list |
| `_SvgNode` | `parse.py` | Internal transient tree node for parsing (not exposed) |

## Numeric Attribute Handling
- Hardcoded set `_NUMERIC_ATTRS`: `cx`, `cy`, `font-size`, `height`, `r`, `width`, `x`, `x1`, `x2`, `y`, `y1`, `y2`
- When a numeric attribute changes, `_numeric_change()` emits **both** `attr_pt` and `attr_mm` keys so callers can use either unit system.
- `font-size` is an exception: only `font_size_pt` is emitted (no mm conversion needed for font sizes).

## Ignored Attributes
`_IGNORED_ATTRS` — `data-page-id`, `data-page-number`, `id`, `label` — are excluded from diff comparison entirely, preventing spurious changes from page IDs or editorial labels.

## Integration
- **Consumed by**: `folio.cli` (via `folio reconcile` command) and any command that calls `folio.reconcile.report`.
- **Depends on**: `folio.render.primitives.pt_to_mm` for unit conversion.
- **Input**: Two SVG file paths and an optional output report path.
- **Output**: JSON report file and/or rich terminal output.
