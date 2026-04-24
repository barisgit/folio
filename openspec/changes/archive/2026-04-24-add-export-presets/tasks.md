## 1. DSL Model and Helpers

- [x] 1.1 Add export preset model types for format, name, scope, viewport, and optional filename pattern in `src/folio/dsl/model.py` or a focused DSL export module.
- [x] 1.2 Add `export_presets` and `default_exports` fields to `Document`, preserving existing document construction defaults.
- [x] 1.3 Add `extra_exports` to `Page`, preserving existing page construction defaults.
- [x] 1.4 Expose `svg()`, `png(name, viewport=...)`, `pdf()`, and `idml()` helper functions from `folio.dsl`.
- [x] 1.5 Add DSL unit tests covering helper defaults, custom PNG names/viewports, document fields, and page `extra_exports` storage.

## 2. Validation

- [x] 2.1 Validate export preset names are unique per document and diagnostics include duplicate names.
- [x] 2.2 Validate `default_exports` references known presets and resolve omitted defaults to `svg` when an SVG preset exists.
- [x] 2.3 Validate page `extra_exports` references known presets and diagnostics include page identity plus unknown names.
- [x] 2.4 Validate page `extra_exports` only references page-scoped presets and rejects document-scoped presets such as `pdf` and `idml`.
- [x] 2.5 Add validation tests for duplicate presets, unknown defaults, unknown page extras, document-scoped page extras, and implicit default behavior.

## 3. Build Target Resolution

- [x] 3.1 Replace `folio build --format` with positional target arguments while keeping `spec_path`, `--out-dir`, `--page`, and `--no-cache` behavior coherent.
- [x] 3.2 Implement target resolution for default builds, explicit named targets, multiple targets, and the reserved `all` target.
- [x] 3.3 Reject unknown build targets with render-error exit behavior and useful diagnostics.
- [x] 3.4 Reject `--page` when requested targets include document-scoped presets.
- [x] 3.5 Add CLI/build tests for default target builds, explicit target builds, multiple targets, `all`, unknown targets, and invalid `--page` combinations.

## 4. Page-Scoped Outputs

- [x] 4.1 Preserve existing SVG page writing and last-build cache behavior for the `svg` preset.
- [x] 4.2 Add PNG preset output generation by rendering participating pages to SVG and rasterizing with the preset viewport.
- [x] 4.3 Implement page participation rules so non-default PNG presets build only pages whose `extra_exports` include the requested preset.
- [x] 4.4 Use default PNG naming of `<svg-stem>_<preset-name>.png`, with room for a preset filename pattern if implemented.
- [x] 4.5 Add tests for SVG output, selected-page PNG derivatives, default page participation, PNG naming, and rasterization failure reporting.

## 5. Document-Scoped Outputs

- [x] 5.1 Preserve existing IDML writing for the `idml` preset and route it through target-based build resolution.
- [x] 5.2 Add PDF preset output generation as a whole-document artifact.
- [x] 5.3 Use document `filename`, document id/name, or existing fallback naming for document-scoped artifact stems.
- [x] 5.4 Add tests for IDML target output, PDF target output, document artifact naming, and document-scoped defaults.

## 6. Rasterize Command Rename

- [x] 6.1 Rename the `preview` command module/registration to `rasterize` and update CLI help text.
- [x] 6.2 Preserve explicit SVG rasterization behavior with default beside-SVG output and `--output` support.
- [x] 6.3 Preserve cached-build rasterization behavior when no explicit SVG is provided, using raster cache naming instead of preview wording.
- [x] 6.4 Ensure automatic viewport derivation reads only root SVG dimensions or root viewBox.
- [x] 6.5 Remove `folio preview` command availability and add tests for the unavailable command plus `folio rasterize` replacements.

## 7. Docs, Examples, and Verification

- [x] 7.1 Update user docs and CLI examples to show `Document(default_exports=[...], export_presets=[...])` and page `extra_exports=[...]`.
- [x] 7.2 Update examples/templates that used `folio preview` or `folio build --format` to use `folio rasterize` and target-based `folio build`.
- [x] 7.3 Update OpenSpec-facing docs or skills if they mention the old preview workflow.
- [x] 7.4 Run focused tests for DSL validation, build outputs, rasterization, PDF/IDML targets, and CLI help.
- [x] 7.5 Run the full project check command and resolve any docs, lint, typecheck, or example failures.
