## Context

Folio currently treats `folio build` as SVG page generation and `folio preview` as a separate SVG-to-PNG raster utility. That works for ad-hoc inspection, but it does not capture project intent when one authored document needs several repeatable outputs: canonical SVG pages, selected-page PNG derivatives at multiple resolutions, whole-document PDF, and whole-document IDML.

The agreed model is to make exports part of the Python DSL and make the CLI target-based. `folio build` resolves named export presets from the loaded document. `folio rasterize` remains the explicit low-level SVG-to-PNG utility.

## Goals / Non-Goals

**Goals:**
- Represent export intent in the DSL using document-level `export_presets` and `default_exports`.
- Support page-scoped presets (`svg`, `png`) and document-scoped presets (`pdf`, `idml`) with validation.
- Let pages opt into extra page-scoped derivatives using `extra_exports` without replacing document defaults.
- Make `folio build` select export targets by name: defaults, explicit presets, or `all`.
- Include PDF as a first-class document-scoped export.
- Rename the low-level raster command from `preview` to `rasterize` without keeping an alias.

**Non-Goals:**
- Designing a full plugin system for custom export backends.
- Preserving backwards compatibility for `folio preview`.
- Implementing advanced imposition, PDF print profiles, or IDML packaging options beyond the first preset model.
- Changing reconcile semantics except for any command/help text that refers to preview artifacts.

## Decisions

1. **Use document-level defaults instead of per-preset defaults.**
   - Decision: `Document(default_exports=["svg"], export_presets=[...])` defines default `folio build` behavior.
   - Rationale: Defaults read as document policy, not as scattered flags on individual presets. It also keeps room for future multi-default builds without changing the API.
   - Alternative considered: `svg(default=True)`. Rejected because it is less readable and encourages ambiguity around whether multiple presets can be default.

2. **Use named preset helpers with explicit scope.**
   - Decision: expose helpers such as `svg()`, `png("1080p", viewport=(1920, 1080))`, `pdf()`, and `idml()` that produce typed export preset values.
   - Rationale: Helpers keep authoring concise while allowing validation to distinguish page-scoped and document-scoped presets.
   - Alternative considered: generic `Export("png", ...)`. Rejected for the first implementation because it is less discoverable and pushes validation details into user-authored strings.

3. **Use `extra_exports` on pages, not `exports`.**
   - Decision: pages opt into non-default page-scoped derivatives with `extra_exports=[...]`.
   - Rationale: `extra_exports` communicates additive behavior. `exports=[...]` could imply that page defaults are replaced, causing edge cases for whether SVG still builds.
   - Alternative considered: page-level `exports`. Rejected because it makes default participation ambiguous.

4. **Make `folio build` target-based.**
   - Decision: `folio build` builds `default_exports`; `folio build 1080p pdf` builds only those targets; `folio build all` builds every preset.
   - Rationale: Named targets match how projects think about deliverables and support multiple raster derivatives from a single source SVG.
   - Alternative considered: `folio build --format png`. Rejected because one format can have multiple named outputs with different viewports and page participation.

5. **Keep rasterization as a low-level utility named `rasterize`.**
   - Decision: replace `folio preview` with `folio rasterize <svg> ...`.
   - Rationale: `rasterize` precisely describes SVG-to-PNG conversion and avoids overloading `render` or `build`.
   - Alternative considered: `folio render`. Rejected because Folio already renders DSL pages to SVG internally, so `render` would be ambiguous.

## Risks / Trade-offs

- **Risk: Build behavior changes are breaking.** → Mitigation: this is acceptable for the current sole-user CLI; update docs, examples, and tests together.
- **Risk: Export presets overlap with existing build/cache behavior.** → Mitigation: preserve SVG rendering and last-build cache semantics for SVG page outputs; layer target resolution above existing rendering.
- **Risk: Document-scoped and page-scoped outputs can be confused.** → Mitigation: validate scope references and reject document-scoped presets in page `extra_exports`.
- **Risk: PDF backend expectations may be unclear.** → Mitigation: specify PDF as a document-scoped preset and keep backend details minimal in this change; implementation can use the existing rendering/raster/PDF capabilities available in the codebase.
- **Risk: `all` target ordering could produce unstable output/test behavior.** → Mitigation: define deterministic order by document order, page order, and preset declaration order.

## Migration Plan

1. Add DSL data structures and helper constructors for export presets.
2. Add validation for preset uniqueness, unknown references, defaults, and scope constraints.
3. Refactor build target resolution before artifact writing.
4. Implement page-scoped SVG/PNG output generation and document-scoped PDF/IDML output generation.
5. Rename the preview command implementation to rasterize and update tests/docs/help text.
6. Update examples to use `default_exports`, `export_presets`, and `extra_exports`.

Rollback strategy: revert the CLI and DSL changes together; the existing SVG build path remains the fallback implementation baseline.

## Open Questions

- Should `Document.default_exports` default to `["svg"]` only when no `export_presets` are declared, or whenever an `svg` preset exists? The proposed behavior is: if omitted, resolve to `svg` when available; otherwise report a validation error.
- What is the first implementation backend for PDF output: SVG-to-PDF conversion per page plus merge, browser print-to-PDF, or a dedicated library? The spec requires behavior but can leave backend choice to implementation.
