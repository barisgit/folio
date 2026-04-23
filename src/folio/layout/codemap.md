# src/folio/layout/

## Responsibility

Pure mathematical layout engine providing immutable, zero-dependency value objects that compute positions and dimensions in millimeter (mm) space. Serves as the authoritative source of truth for grid/column arithmetic used by DSL document builders.

## Design

### Architecture

All layout helpers are **frozen dataclasses** — immutable value objects with named fields and factory classmethods. No side effects, no state.

Three core primitives:

| Class | Role | Key Methods |
|---|---|---|
| `Columns` | 1D horizontal partitioning (1-indexed) | `x()`, `bounds()` |
| `Grid` | 2D cell matrix (row-major, 1-indexed) | `cell_origin()`, `cell_bounds()` |
| `FlowColumns` | Multi-panel sequence with arrow lanes | `panel_x()`, `panel_bounds()`, `arrow_x()`, `arrow_center_x()` |

### Factory Helpers

Convenience wrappers over the dataclass constructors that use Python `float` keyword args (mm suffix renamed):

- `cols(n, *, inside=(left, right), gap=0.0)` → `Columns.from_inside()`
- `grid(cols, rows, *, inside=(x, y, w, h), col_gap=0.0, row_gap=0.0)` → `Grid.from_inside()`
- `flow_cols(n=3, *, inside=(x, y, w), gap=0.0, arrow_w=0.0)` → `FlowColumns.from_inside()`

### Validation

Every factory method enforces preconditions with `ValueError`:
- `count` / `columns` / `rows` must be positive integers
- Computed cell/column widths must be strictly positive after subtracting gaps

### Pattern: Value Object + Builder Pattern

The `from_bounds` / `from_inside` classmethods follow a two-stage builder: raw numeric args → normalized internal representation. This decouples caller intent (e.g., "fit inside these edges") from internal storage (normalized `origin_x_mm`, `column_width_mm`).

## Flow

### Data in
- Caller provides mm-space numeric bounds or edges: `(x, y)`, `(x, y, w)`, or `(x, y, w, h)` tuples
- Optional gap/arrow-width parameters control spacing between cells/panels

### Arithmetic
- `Columns`: `column_width_mm = (width_mm - ((count - 1) * gap_mm)) / count`
- `Grid`: `cell_width_mm = (width_mm - ((columns - 1) * column_gap_mm)) / columns`; rows use same formula
- `FlowColumns`: accounts for both inter-column gaps and arrow lanes: `column_width_mm = (width_mm - ((count - 1) * arrow_width_mm) - (2 * (count - 1) * gap_mm)) / count`

### Data out
- `x(index)` / `cell_origin(index)` → `(x_mm, y_mm)` tuple
- `bounds(index)` / `cell_bounds(index)` → `(x, y, w, h)` tuple
- `panel_bounds(index, height_mm)` / `arrow_x(index)` / `arrow_center_x(index)` → panel and arrow geometry

## Integration

- **Consumed by**: Starter template (`src/folio/templates/starter/pages.py`) — calls `grid()` to position card layouts; template uses layout results to place DSL elements
- **Depends on**: Nothing in the folio package (pure Python, stdlib only)
- **Validated by**: `tests/test_layout.py`
- **Specified in**: `openspec/specs/layout-helpers/spec.md`
