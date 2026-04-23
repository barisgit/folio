# Capability: Chart Embedding

## Purpose

Describe Folio's optional matplotlib-backed chart primitive for embedding charts into authored pages.

## Requirements

### Requirement: Optional chart dependency
Folio SHALL treat chart rendering as an optional capability that requires matplotlib at runtime.

#### Scenario: Missing matplotlib
- **WHEN** a user invokes `chart()` without matplotlib installed
- **THEN** Folio raises a runtime error describing the optional dependency requirement

### Requirement: Three chart authoring modes
Folio SHALL support decorator, context-manager, and pre-built-figure flows for charts.

#### Scenario: Decorator mode
- **WHEN** a user decorates a function with `@chart(...)`
- **THEN** Folio creates a matplotlib figure and axes
- **AND** rasterizes the result into a Folio image element after the function draws into the axes

#### Scenario: Context-manager mode
- **WHEN** a user enters `with chart(...) as ax:`
- **THEN** Folio yields a matplotlib axes object for drawing
- **AND** exposes the resulting image element after the context exits successfully

#### Scenario: Pre-built figure mode
- **WHEN** a user calls `chart(...).from_figure(fig)`
- **THEN** Folio rasterizes that existing matplotlib figure into a Folio image element

### Requirement: Chart placement and validation
Folio SHALL treat a chart as an image element placed in millimeter coordinates.

#### Scenario: Chart placement
- **WHEN** a chart is created with `x_mm`, `y_mm`, `width_mm`, and `height_mm`
- **THEN** the resulting chart participates in normal Folio page layout as an image element at that position and size

#### Scenario: Invalid chart dimensions
- **WHEN** a chart is created without an element id, with non-positive dimensions, or with non-positive dpi
- **THEN** Folio rejects the chart configuration with a type error

### Requirement: Content-addressed chart caching
Folio SHALL cache rendered chart PNGs by content hash.

#### Scenario: Default cache location
- **WHEN** a chart is rasterized without a cache override
- **THEN** Folio stores the PNG in `<spec_dir>/.folio-cache/charts/`

#### Scenario: Cache anchor without a loaded spec
- **WHEN** chart caching is used outside the normal DSL loader flow
- **THEN** Folio falls back to the current working directory as the default cache anchor

#### Scenario: Cache overrides
- **WHEN** a user provides `cache_dir=` or sets `FOLIO_CHART_CACHE_DIR`
- **THEN** Folio uses that location instead of the default chart cache path

#### Scenario: Reusing identical chart output
- **WHEN** repeated builds produce identical PNG bytes for the same chart
- **THEN** Folio reuses the existing cached PNG file instead of writing a duplicate copy

### Requirement: Default chart rendering choices
Folio SHALL default chart rasterization for print-oriented page work.

#### Scenario: Default rendering configuration
- **WHEN** a user does not override chart rendering options
- **THEN** Folio uses `dpi=300`
- **AND** renders with a transparent background by default

### Requirement: Figure lifecycle ownership
Folio SHALL close figures it creates itself and leave caller-owned figures alone.

#### Scenario: Folio-owned figure lifecycle
- **WHEN** a chart is used as a decorator or context manager
- **THEN** Folio closes the matplotlib figure after rasterization

#### Scenario: Caller-owned figure lifecycle
- **WHEN** a chart is created from an existing figure via `from_figure()`
- **THEN** Folio rasterizes the figure without assuming ownership of its lifecycle
