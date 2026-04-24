## ADDED Requirements

### Requirement: Export preset DSL
Folio SHALL allow a document to declare named export presets for supported output types.

#### Scenario: Built-in preset helpers
- **WHEN** a spec defines `export_presets=[svg(), png("1080p", viewport=(1920, 1080)), pdf(), idml()]`
- **THEN** Folio registers the preset names `svg`, `1080p`, `pdf`, and `idml`
- **AND** associates each preset with its output format and scope

#### Scenario: Unique preset names
- **WHEN** two export presets in the same document use the same name
- **THEN** Folio reports a validation error
- **AND** does not build ambiguous outputs

#### Scenario: Unknown preset references
- **WHEN** a document default, CLI build target, or page extra export references an unknown preset name
- **THEN** Folio reports a validation error
- **AND** includes the unknown preset name in the diagnostic

### Requirement: Document-level default exports
Folio SHALL define default build behavior at the document level rather than on individual presets.

#### Scenario: Single default export
- **WHEN** a document declares `default_exports=["svg"]`
- **THEN** `folio build` builds only the `svg` preset by default
- **AND** non-default presets are built only when explicitly requested or when building `all`

#### Scenario: Missing default export
- **WHEN** a document omits `default_exports`
- **THEN** Folio treats `svg` as the implicit default when an `svg` preset exists
- **AND** reports a validation error if no implicit default can be resolved

#### Scenario: Document-scoped default export
- **WHEN** `default_exports` references a document-scoped preset such as `pdf` or `idml`
- **THEN** Folio accepts that preset as the default build output
- **AND** `folio build` builds that document-scoped artifact instead of page SVGs

### Requirement: Page extra exports
Folio SHALL let pages opt into additional page-scoped export presets without replacing document defaults.

#### Scenario: Extra raster exports for one page
- **WHEN** a page declares `extra_exports=["1080p", "4k"]`
- **THEN** explicit builds of `1080p` or `4k` include that page
- **AND** the page still participates in document default exports when those defaults are built

#### Scenario: Pages without extra exports
- **WHEN** a page omits `extra_exports`
- **THEN** Folio builds that page only for page-scoped default exports
- **AND** skips non-default page-scoped presets for that page

#### Scenario: Document-scoped presets on pages
- **WHEN** a page references `pdf`, `idml`, or another document-scoped preset in `extra_exports`
- **THEN** Folio reports a validation error
- **AND** explains that page extra exports may only reference page-scoped presets

### Requirement: Target-based build workflow
Folio SHALL build named export targets from the DSL rather than requiring format-specific command flags.

#### Scenario: Default build
- **WHEN** a user runs `folio build`
- **THEN** Folio builds the document's `default_exports`
- **AND** writes artifacts to the resolved output directory

#### Scenario: Explicit target build
- **WHEN** a user runs `folio build 1080p` or `folio build pdf`
- **THEN** Folio builds only the requested preset
- **AND** does not also build default exports unless they are explicitly requested

#### Scenario: Multiple target build
- **WHEN** a user runs `folio build 1080p 4k`
- **THEN** Folio builds each requested preset once
- **AND** reports an error if any requested target is unknown

#### Scenario: All target build
- **WHEN** a user runs `folio build all`
- **THEN** Folio builds every export preset declared by the document
- **AND** preserves deterministic output ordering by document order, page order, and preset declaration order

### Requirement: Page-scoped export outputs
Folio SHALL write one artifact per participating page for page-scoped presets.

#### Scenario: SVG preset output
- **WHEN** Folio builds the `svg` preset for a page
- **THEN** it writes the rendered SVG using the page filename
- **AND** uses the current SVG rendering and cache behavior

#### Scenario: PNG preset output
- **WHEN** Folio builds a PNG preset for a participating page
- **THEN** it rasterizes that page's rendered SVG using the preset viewport
- **AND** writes a PNG artifact using the page SVG stem plus the preset name by default

#### Scenario: PNG output naming
- **WHEN** page `TM42_brochure_p3_16x9.svg` builds preset `1080p`
- **THEN** Folio writes `TM42_brochure_p3_16x9_1080p.png` unless the preset overrides the filename pattern

#### Scenario: PNG rasterization failure
- **WHEN** all available PNG rasterization backends fail
- **THEN** Folio reports a build error for that preset
- **AND** does not silently emit a partial or empty PNG

### Requirement: Document-scoped export outputs
Folio SHALL write one artifact per document for document-scoped presets.

#### Scenario: IDML preset output
- **WHEN** Folio builds the `idml` preset
- **THEN** it packages the whole document as an IDML artifact
- **AND** writes the IDML file to the resolved output directory

#### Scenario: PDF preset output
- **WHEN** Folio builds the `pdf` preset
- **THEN** it exports the whole document as a PDF artifact
- **AND** writes the PDF file to the resolved output directory

#### Scenario: Document artifact naming
- **WHEN** a document declares a name or filename stem
- **THEN** document-scoped exports use that stem by default
- **AND** otherwise fall back to Folio's existing document artifact naming behavior

### Requirement: Low-level rasterize command
Folio SHALL keep SVG-to-PNG rasterization available as an explicit utility separate from target-based document builds.

#### Scenario: Rasterizing an explicit SVG
- **WHEN** a user runs `folio rasterize out/page.svg --viewport 1920x1080`
- **THEN** Folio writes a PNG beside the SVG by default
- **AND** uses the same rasterization backend chain as PNG export presets

#### Scenario: Explicit raster output path
- **WHEN** a user passes `--output`
- **THEN** Folio writes the rasterized PNG to that path
- **AND** does not require the SVG to be part of a Folio build cache
