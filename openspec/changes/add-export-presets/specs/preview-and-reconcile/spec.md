## RENAMED Requirements

FROM: `Previewing explicit SVG files`
TO: `Rasterizing explicit SVG files`

FROM: `Previewing cached build pages`
TO: `Rasterizing cached build pages`

## MODIFIED Requirements

### Requirement: Rasterizing explicit SVG files
Folio SHALL rasterize an explicit SVG file to PNG through the `folio rasterize` command.

#### Scenario: Default raster output path
- **WHEN** a user runs `folio rasterize <svg>` without `--output`
- **THEN** Folio writes a PNG beside that SVG using the same stem

#### Scenario: Explicit raster output path
- **WHEN** a user passes `--output` with an explicit SVG path
- **THEN** Folio writes the PNG to the requested location

#### Scenario: Invalid output usage
- **WHEN** a user passes `--output` without an explicit SVG argument
- **THEN** Folio rejects the command instead of guessing a target file

### Requirement: Rasterizing cached build pages
Folio SHALL rasterize cached last-build pages for a spec when no explicit SVG path is provided.

#### Scenario: Spec-based rasterization
- **WHEN** a user runs `folio rasterize --spec <spec>` or `folio rasterize` inside a project with cached pages
- **THEN** Folio loads the cached last-build SVGs for that spec
- **AND** writes PNG rasters into that spec's raster cache area

### Requirement: Viewport handling and renderer fallback
Folio SHALL derive a raster viewport from the SVG when possible and fall back across multiple raster backends.

#### Scenario: Automatic viewport
- **WHEN** the user does not provide `--viewport`
- **THEN** Folio derives the viewport from the root SVG `width` and `height` attributes or root `viewBox`
- **AND** falls back to an A4-sized default viewport if neither is available

#### Scenario: Explicit viewport
- **WHEN** a user passes `--viewport WIDTHxHEIGHT`
- **THEN** Folio uses that exact raster viewport
- **AND** rejects malformed or non-positive viewport values

#### Scenario: Renderer fallback order
- **WHEN** Folio rasterizes an SVG
- **THEN** it tries Playwright first
- **AND** falls back in order to CairoSVG, `rsvg-convert`, and Inkscape until one succeeds

#### Scenario: Rasterization failures
- **WHEN** rasterization cannot find cached inputs, cannot read the requested SVG, or all raster renderers fail
- **THEN** Folio exits with status code `2`

## REMOVED Requirements

### Requirement: Preview command name
**Reason**: The `preview` command name is ambiguous now that PNG outputs can be intentional build derivatives rather than visual inspection artifacts.
**Migration**: Use `folio rasterize` for low-level SVG-to-PNG conversion and `folio build <target>` for DSL-declared PNG export presets.

#### Scenario: Preview command is unavailable
- **WHEN** a user runs `folio preview`
- **THEN** Folio reports that the command is unavailable
- **AND** directs the user to `folio rasterize` or target-based `folio build`
