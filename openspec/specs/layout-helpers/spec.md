# Capability: Layout Helpers

## Purpose

Describe Folio's reusable helpers for computing document grids, columns, and panel flows in millimeter space.

## Requirements

### Requirement: Column layouts
Folio SHALL compute evenly sized columns from either explicit bounds or inside edges.

#### Scenario: Columns from bounds
- **WHEN** a user creates `Columns.from_bounds(start_mm, width_mm, count, gap_mm)`
- **THEN** Folio computes an equal `column_width_mm` across the requested count
- **AND** `x(index)` and `bounds(index)` return the position and width for each 1-based column

#### Scenario: Invalid column configuration
- **WHEN** the column count is not positive or the computed width would be non-positive
- **THEN** Folio raises a `ValueError`

### Requirement: Grid layouts
Folio SHALL compute grid cells from bounding rectangles and gap settings.

#### Scenario: Grid from inside bounds
- **WHEN** a user calls `grid(cols, rows, inside=(x, y, width, height), col_gap=..., row_gap=...)`
- **THEN** Folio computes cell width and height from the available space
- **AND** exposes `cell_origin(index)` and `cell_bounds(index)` for 1-based cell addressing

#### Scenario: Grid index validation
- **WHEN** a user requests a grid cell index below `1`
- **THEN** Folio raises a `ValueError`
- **AND** positive indexes continue to map through the grid geometry even if the authored layout does not impose an explicit upper bound

#### Scenario: Invalid grid configuration
- **WHEN** rows or columns are not positive or the computed cell dimensions would be non-positive
- **THEN** Folio raises a `ValueError`

### Requirement: Flow column layouts
Folio SHALL support multi-panel flow layouts with optional arrow lanes between panels.

#### Scenario: Flow panels with arrows
- **WHEN** a user creates `flow_cols()` with `gap` and `arrow_w`
- **THEN** Folio computes panel bounds and arrow positions across the available width
- **AND** exposes `panel_x`, `panel_bounds`, `arrow_x`, and `arrow_center_x`

#### Scenario: Invalid flow configuration
- **WHEN** the panel count is not positive or the computed flow panel width would be non-positive
- **THEN** Folio raises a `ValueError`
