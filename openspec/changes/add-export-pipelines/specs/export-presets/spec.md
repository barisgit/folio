## MODIFIED Requirements

### Requirement: Export preset DSL
Folio SHALL allow a document to declare named export presets for supported output types, including optional source dependencies for presets that consume other preset artifacts.

#### Scenario: Built-in preset helpers
- **WHEN** a spec defines `export_presets=[svg(), png("1080p", viewport=(1920, 1080)), pdf("screen", source="1080p"), idml()]`
- **THEN** Folio registers the preset names `svg`, `1080p`, `screen`, and `idml`
- **AND** associates each preset with its output format, scope, and source dependency when present

#### Scenario: Unique preset names
- **WHEN** two export presets in the same document use the same name
- **THEN** Folio reports a validation error
- **AND** does not build ambiguous outputs

#### Scenario: Unknown preset references
- **WHEN** a document default, CLI build target, page extra export, or preset source references an unknown preset name
- **THEN** Folio reports a validation error
- **AND** includes the unknown preset name in the diagnostic

#### Scenario: Source metadata storage
- **WHEN** a preset helper is called with `source="1080p"`
- **THEN** Folio stores that source name on the export preset model
- **AND** makes it available to export validation and build planning

### Requirement: Page-scoped export outputs
Folio SHALL write one artifact per participating page for page-scoped presets and SHALL use pipeline sources to produce dependent page artifacts.

#### Scenario: SVG preset output
- **WHEN** Folio builds the `svg` preset for a page
- **THEN** it writes the rendered SVG using the page filename
- **AND** uses the current SVG rendering and cache behavior

#### Scenario: PNG preset output
- **WHEN** Folio builds a PNG preset for a participating page
- **THEN** it rasterizes that page from the preset's resolved SVG source
- **AND** writes a PNG artifact using the page SVG stem plus the preset name by default

#### Scenario: PNG output naming
- **WHEN** page `TM42_brochure_p3_16x9.svg` builds preset `1080p`
- **THEN** Folio writes `TM42_brochure_p3_16x9_1080p.png` unless the preset overrides the filename pattern

#### Scenario: PNG rasterization failure
- **WHEN** all available PNG rasterization backends fail
- **THEN** Folio reports a build error for that preset
- **AND** does not silently emit a partial or empty PNG

#### Scenario: PNG source compatibility
- **WHEN** a PNG preset declares a source preset
- **THEN** Folio accepts the source only if it resolves to a page-scoped SVG artifact
- **AND** rejects incompatible sources before rasterization starts

### Requirement: Document-scoped export outputs
Folio SHALL write one artifact per document for document-scoped presets and SHALL use pipeline sources to produce dependent document artifacts.

#### Scenario: IDML preset output
- **WHEN** Folio builds the `idml` preset
- **THEN** it packages the whole document as an IDML artifact
- **AND** writes the IDML file to the resolved output directory

#### Scenario: PDF preset output
- **WHEN** Folio builds a PDF preset sourced from a supported page artifact preset
- **THEN** it exports the whole document as a PDF artifact from those source artifacts
- **AND** the PDF pages visually contain the rendered Folio page output
- **AND** writes the PDF file to the resolved output directory

#### Scenario: PDF page order and count
- **WHEN** Folio builds the `pdf` preset for a document with multiple pages
- **THEN** the PDF contains one page for each document page
- **AND** orders PDF pages by Folio page order

#### Scenario: PDF export failure
- **WHEN** Folio cannot produce source artifacts or assemble one or more pages needed for a PDF preset
- **THEN** it reports a build/render error for the PDF target
- **AND** does not silently emit a blank, partial, or misleading PDF artifact

#### Scenario: Document artifact naming
- **WHEN** a document declares a name or filename stem
- **THEN** document-scoped exports use that stem by default
- **AND** otherwise fall back to Folio's existing document artifact naming behavior
