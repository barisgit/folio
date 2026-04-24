## Why

Folio's current build and preview workflow treats SVG output and ad-hoc PNG previewing as separate commands, but real projects need named, repeatable export targets such as page SVGs, 1080p/4k PNG derivatives, PDF, and IDML from one document definition. Defining these outputs in the DSL makes the build workflow clearer, reproducible, and less dependent on one-off command flags.

## What Changes

- Add first-class export preset declarations to the Python DSL, including `svg()`, `png(...)`, `pdf()`, and `idml()` helpers.
- Add document-level default export selection via `default_exports=[...]` rather than per-preset `default=True` flags.
- Add page-level `extra_exports=[...]` for opt-in page-scoped derivatives such as selected-page 1080p/4k PNGs.
- Change `folio build` to a target-based workflow: default exports when no target is supplied, explicit named targets such as `1080p`, `pdf`, or `idml`, and `all` for every declared preset.
- Include PDF as a document-scoped export alongside IDML.
- Rename the low-level SVG-to-PNG utility from `preview` to `rasterize` and keep it separate from document target builds.
- **BREAKING**: `folio preview` is replaced by `folio rasterize`; no backwards-compatible alias is required because this is currently a sole-user CLI.

## Capabilities

### New Capabilities
- `export-presets`: Defines named document export presets, preset scopes, document defaults, page extra exports, target-based builds, page-scoped SVG/PNG artifacts, document-scoped PDF/IDML artifacts, and the low-level rasterize command.

### Modified Capabilities
- `python-dsl`: Document and page structures gain export preset fields and validation semantics.
- `build-and-validate`: Build command behavior changes from always rendering SVG pages by default to resolving named export targets and producing the corresponding artifacts.
- `preview-and-reconcile`: The raster preview capability is renamed/reframed as `rasterize`, while reconcile behavior remains unchanged.

## Impact

- Affected CLI commands: `folio build`, `folio preview` removal/rename, new `folio rasterize` command.
- Affected DSL/API: `Document` accepts `name`, `default_exports`, and `export_presets`; pages accept `extra_exports`; export helper functions are exposed from the DSL.
- Affected output behavior: builds may produce page-scoped SVG/PNG artifacts and document-scoped PDF/IDML artifacts according to requested targets.
- Affected validation: preset names, target references, default exports, page extra exports, and preset scope usage require diagnostics.
- Affected tests/docs: build workflow tests, rasterization tests, DSL docs, CLI help, and examples need updates.
