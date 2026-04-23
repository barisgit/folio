# Capability: Preview and Reconcile

## Purpose

Describe Folio's raster preview generation and SVG reconciliation workflow against cached builds.

## Requirements

### Requirement: Previewing explicit SVG files
Folio SHALL rasterize an explicit SVG file to PNG.

#### Scenario: Default preview output path
- **WHEN** a user runs `folio preview <svg>` without `--output`
- **THEN** Folio writes a PNG beside that SVG using the same stem

#### Scenario: Explicit preview output path
- **WHEN** a user passes `--output` with an explicit SVG path
- **THEN** Folio writes the PNG to the requested location

#### Scenario: Invalid output usage
- **WHEN** a user passes `--output` without an explicit SVG argument
- **THEN** Folio rejects the command instead of guessing a target file

### Requirement: Previewing cached build pages
Folio SHALL preview cached last-build pages for a spec when no explicit SVG path is provided.

#### Scenario: Spec-based preview
- **WHEN** a user runs `folio preview --spec <spec>` or `folio preview` inside a project with cached pages
- **THEN** Folio loads the cached last-build SVGs for that spec
- **AND** writes PNG previews into that spec's preview cache area

### Requirement: Viewport handling and renderer fallback
Folio SHALL derive a raster viewport from the SVG when possible and fall back across multiple raster backends.

#### Scenario: Automatic viewport
- **WHEN** the user does not provide `--viewport`
- **THEN** Folio derives the viewport from the SVG `width`/`height` attributes or `viewBox`
- **AND** falls back to an A4-sized default viewport if neither is available

#### Scenario: Explicit viewport
- **WHEN** a user passes `--viewport WIDTHxHEIGHT`
- **THEN** Folio uses that exact raster viewport
- **AND** rejects malformed or non-positive viewport values

#### Scenario: Renderer fallback order
- **WHEN** Folio rasterizes a preview
- **THEN** it tries Playwright first
- **AND** falls back in order to CairoSVG, `rsvg-convert`, and Inkscape until one succeeds

#### Scenario: Preview failures
- **WHEN** preview cannot find cached inputs, cannot read the requested SVG, or all preview renderers fail
- **THEN** Folio exits with status code `2`

### Requirement: Reconciling edited SVGs against cached builds
Folio SHALL compare edited SVGs to the cached last build for the same spec and page.

#### Scenario: Single edited SVG
- **WHEN** a user runs `folio reconcile <edited.svg> --spec <spec>`
- **THEN** Folio resolves the target page number from `--page`, the edited SVG metadata, or the edited filename when needed
- **AND** compares that edited SVG against the cached last-build SVG for the same page

#### Scenario: Reconciling all cached pages
- **WHEN** a user runs `folio reconcile --all --edited-dir <dir> --spec <spec>`
- **THEN** Folio compares every cached page against the same-named edited SVG in that directory
- **AND** fails if any expected edited SVG is missing

### Requirement: Structured diff behavior
Folio SHALL report attribute and text changes for stable ids while treating unmatched additions and deletions as warnings.

#### Scenario: Attribute and text diffs
- **WHEN** a matching element id exists in both base and edited SVGs
- **THEN** Folio reports changed text and changed attributes for that element
- **AND** numeric geometry changes are reported in both points and millimeters where applicable

#### Scenario: Ignored metadata attributes
- **WHEN** Folio compares matching elements
- **THEN** it ignores differences in `id`, `data-page-id`, `data-page-number`, and `label`

#### Scenario: Added or deleted elements
- **WHEN** an element exists only in the edited SVG or only in the cached SVG
- **THEN** Folio reports that as a warning rather than an attribute change

### Requirement: Reconcile reporting and exit behavior
Folio SHALL emit both human-readable output and machine-readable JSON reports.

#### Scenario: Report file generation
- **WHEN** reconcile runs for a page
- **THEN** Folio writes a JSON report into the spec's reconcile cache directory
- **AND** includes the report path in the returned payload/output

#### Scenario: JSON CLI output
- **WHEN** a user passes `--format json`
- **THEN** Folio emits machine-readable JSON for one page or all pages

#### Scenario: Exit codes
- **WHEN** reconcile encounters missing cache state, missing files, or SVG parse errors
- **THEN** it exits with status code `2`

#### Scenario: Differences detected
- **WHEN** reconcile finds one or more changes
- **THEN** it exits with status code `3`
