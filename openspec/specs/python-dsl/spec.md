# Capability: Python DSL

## Purpose

Describe Folio's core Python-first authoring model for defining documents, pages, and SVG elements.

## Requirements

### Requirement: Self-contained Python specs
Folio SHALL treat a Python file as the source of truth for a document spec, with `build.py` as the default entrypoint for project-style specs.

#### Scenario: Default spec resolution
- **WHEN** a CLI command that accepts a spec path is run without an explicit path
- **THEN** Folio resolves the spec to `./build.py` in the current working directory

#### Scenario: Project directory resolution
- **WHEN** a user passes a directory instead of a Python file
- **THEN** Folio resolves the spec to `<directory>/build.py`
- **AND** sibling modules in that directory are importable by the spec during execution

### Requirement: Immutable document model
Folio SHALL represent authored output as immutable document structures composed of documents, pages, elements, defs, and text spans.

#### Scenario: Accepted module entry shapes
- **WHEN** a DSL module defines `document`, `pages`, or a callable `build()`
- **THEN** Folio accepts that module as a valid spec entrypoint
- **AND** coerces the authored value into a document before validation and rendering

#### Scenario: Building a document
- **WHEN** a valid spec entrypoint is loaded
- **THEN** the document contains an ordered collection of pages
- **AND** each page carries a page id, page number, filename, dimensions, elements, and optional defs/attrs

### Requirement: Page rendering order and metadata
Folio SHALL render one SVG file per page, ordered by `page_number`, and preserve page metadata in the SVG output.

#### Scenario: Rendering multiple pages
- **WHEN** a document contains multiple pages
- **THEN** Folio renders them in ascending `page_number` order
- **AND** each rendered page includes page metadata such as `data-page-id` and `data-page-number`

### Requirement: SVG authoring primitives
Folio SHALL expose Python builders for the core SVG and document primitives used by specs.

#### Scenario: Authoring page content
- **WHEN** a user writes a spec against `folio.dsl`
- **THEN** they can compose pages from primitives including text, image, rect, circle, ellipse, polygon, polyline, line, path, group, rule, triangle, and QR output
- **AND** they can define reusable defs such as gradients, masks, clip paths, filters, and raw SVG nodes

### Requirement: Coordinate system and page sizing
Folio SHALL author geometry in millimeters and allow page size overrides per page.

#### Scenario: Rendering mm-based geometry
- **WHEN** a spec provides positions and sizes in millimeters
- **THEN** Folio converts those values to SVG point-space for rendering
- **AND** keeps the authored page width and height in the SVG root attributes

#### Scenario: Using non-default page sizes
- **WHEN** a page specifies `width_mm` and `height_mm`
- **THEN** Folio renders the page with those dimensions instead of the default A4 size

### Requirement: Element identifiers
Folio SHALL preserve explicit element ids and generate ids for elements that omit them.

#### Scenario: Stable authored ids
- **WHEN** a user supplies an explicit element id
- **THEN** Folio uses that id in the rendered SVG
- **AND** that id is available to downstream reconcile workflows

#### Scenario: Generated ids
- **WHEN** an element omits its id
- **THEN** Folio generates a kind-based id for rendering
- **AND** users SHOULD prefer explicit ids for reconcile-stable output because generated ids are build-local conveniences rather than durable authored identifiers

#### Scenario: Duplicate ids
- **WHEN** two elements or text spans reuse the same id within a rendered page tree
- **THEN** Folio rejects the document with a render error instead of emitting ambiguous SVG ids

### Requirement: Embedded image assets
Folio SHALL embed referenced image assets into rendered SVG output.

#### Scenario: Rendering an image element
- **WHEN** a spec references an image asset reachable from the spec directory
- **THEN** Folio embeds the image into the SVG as a data URI
- **AND** the resulting SVG does not depend on an external runtime image reference

### Requirement: Scoped reusable blocks
Folio SHALL support reusable scoped authoring blocks with local coordinates and namespaced ids.

#### Scenario: Building a component block
- **WHEN** a user creates a `block()` rooted at a page position
- **THEN** child elements can be authored in local coordinates
- **AND** child ids are namespaced by the block id in rendered output
