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

### Requirement: Export preset authoring fields
Folio SHALL expose document and page fields for declaring export presets, default exports, and page extra exports in Python specs.

#### Scenario: Document declares export presets
- **WHEN** a Python spec creates a `Document` with `export_presets=[svg(), idml(), pdf(), png("1080p", viewport=(1920, 1080))]`
- **THEN** Folio stores those presets on the document model
- **AND** makes the preset names available to validation and build target resolution

#### Scenario: Document declares default exports
- **WHEN** a Python spec creates a `Document` with `default_exports=["svg"]`
- **THEN** Folio stores that default export list on the document model
- **AND** uses it as the default target set for `folio build`

#### Scenario: Page declares extra exports
- **WHEN** a Python spec creates a page with `extra_exports=["1080p", "4k"]`
- **THEN** Folio stores those extra export references on the page model
- **AND** uses them to decide page participation for non-default page-scoped presets

#### Scenario: Export helper functions are available
- **WHEN** a user imports from `folio.dsl`
- **THEN** the user can access `svg`, `png`, `pdf`, and `idml` export preset helper functions
- **AND** each helper returns a value accepted by `Document(export_presets=[...])`

### Requirement: Export preset validation in DSL documents
Folio SHALL validate export preset declarations and references as part of document validation.

#### Scenario: Duplicate preset names
- **WHEN** a document contains multiple export presets with the same name
- **THEN** Folio rejects the document with a validation error
- **AND** includes the duplicate preset name in the diagnostic

#### Scenario: Unknown default export
- **WHEN** `default_exports` references a preset that is not declared by the document
- **THEN** Folio rejects the document with a validation error
- **AND** includes the unknown preset name in the diagnostic

#### Scenario: Unknown page extra export
- **WHEN** a page `extra_exports` entry references a preset that is not declared by the document
- **THEN** Folio rejects the document with a validation error
- **AND** includes the page id or page number and unknown preset name in the diagnostic

#### Scenario: Page references document-scoped preset
- **WHEN** a page `extra_exports` entry references a document-scoped preset such as `pdf` or `idml`
- **THEN** Folio rejects the document with a validation error
- **AND** explains that `extra_exports` accepts only page-scoped presets

### Requirement: Tweak helpers in the public DSL

Folio SHALL expose design-time tweak helpers through the public Python DSL surface.

#### Scenario: Importing tweak helpers
- **WHEN** a user imports `from folio.dsl import tweaks`
- **THEN** the imported `tweaks` namespace provides helpers for declaring tweak groups and supported tweak value types
- **AND** the namespace is available anywhere other public DSL symbols are available

#### Scenario: Implementation lives under folio.core.dsl
- **WHEN** a maintainer inspects the public DSL facade
- **THEN** the tweak implementation lives at `folio.core.dsl.tweaks`
- **AND** is re-exported from `folio.dsl.tweaks` so user-facing imports use the public path

#### Scenario: Public tweak helper documentation
- **WHEN** a tweak helper is part of the public DSL surface
- **THEN** it has a docstring and examples suitable for the generated DSL docs index

### Requirement: Tweak values in authored specs

Folio SHALL allow resolved tweak values to be used in authored specs anywhere the corresponding primitive value type is accepted.

#### Scenario: Tweak color in shape attribute
- **WHEN** a spec passes a color tweak value to `rect(..., fill=theme.primary)`
- **THEN** Folio accepts the authored element
- **AND** render/build uses the resolved color value for the SVG `fill` attribute

#### Scenario: Tweak number in text style
- **WHEN** a spec passes a numeric tweak value to `TextStyle(font_size_pt=theme.hero_size_pt)`
- **THEN** Folio accepts the authored text style
- **AND** render/build uses the resolved numeric value for the SVG `font-size` attribute

#### Scenario: Tweak value in Python expressions
- **WHEN** a spec coerces a tweak value to a primitive and derives another value from it
- **THEN** Folio uses the derived value correctly during render/build
- **AND** the derived value is treated as rebuild-required

### Requirement: TweakValue preservation on live-eligible fields

Folio SHALL accept `TweakValue` on live-eligible style and element-attribute fields without coercing it to a primitive at construction time.

#### Scenario: TextStyle preserves TweakValue for font_size_pt
- **WHEN** a spec assigns a `TweakValue` returned by `tweaks.size_pt(...)` to `TextStyle(font_size_pt=...)`
- **THEN** the resulting `TextStyle` instance stores the `TweakValue` wrapper
- **AND** does not eagerly convert it to `float`

#### Scenario: TextStyle preserves TweakValue for fill
- **WHEN** a spec assigns a `TweakValue` returned by `tweaks.color(...)` to `TextStyle(fill=...)`
- **THEN** the resulting `TextStyle` instance stores the `TweakValue` wrapper
- **AND** does not eagerly convert it to `str`

#### Scenario: Live-eligible element attributes accept TweakValue
- **WHEN** a spec passes a `TweakValue` to an element attribute that the renderer treats as live-eligible (for example `fill`, `stroke`, opacity attributes, or `letter_spacing`)
- **THEN** the element accepts the value without primitive coercion at construction
- **AND** renderer build mode resolves the value to a concrete primitive at the attribute boundary

### Requirement: Spec-scoped tweak registry visibility

Folio SHALL expose tweak declarations collected during a spec load through the spec load/render service helper without leaking declarations between specs.

#### Scenario: Declarations in imported theme module are visible
- **WHEN** `build.py` imports `theme.py` and `theme.py` declares tweak groups
- **THEN** the registry snapshot returned by the service helper contains those declarations

#### Scenario: Registry isolation across loads
- **WHEN** Folio loads two different specs sequentially in one process
- **THEN** the registry snapshot for the second spec contains only that spec's declarations
