## Context

Folio now has named export presets (`svg`, `png`, `pdf`, `idml`) and target-based builds, but target execution is still mostly direct. The quick PDF backend proves the limitation: PDF needs rendered SVG content and often a raster source, but that dependency is hidden inside the PDF writer instead of being represented as a reusable build graph.

The next step is to make export execution explicit: resolve requested targets, plan their dependencies, and run a deterministic DAG of built-in export steps. This should support immediate quality improvements such as `pdf(source="1080p")` while preserving the `pdf` target name, and it should leave true SVG-to-vector-PDF conversion for later.

## Goals / Non-Goals

**Goals:**
- Model export execution as a typed dependency graph with deterministic planning and ordering.
- Let presets declare a source preset where applicable, e.g. `png("1080p", source="svg")` and `pdf(source="1080p")`.
- Validate graph correctness before execution: unknown sources, scope/type incompatibility, cycles, and unsupported backend routes.
- Reuse intermediate artifacts within a build so dependent targets do not re-render or re-rasterize unnecessarily.
- Keep CLI behavior stable: `folio build`, `folio build 1080p`, `folio build pdf`, and `folio build all` remain target-based.

**Non-Goals:**
- Third-party pipeline/plugin APIs.
- Perfect vector/editable PDF output in this change.
- General-purpose workflow orchestration beyond built-in Folio export targets.
- User-facing graph language beyond preset source/dependency fields.

## Decisions

### Typed artifact graph

Represent pipeline nodes by preset name and artifact type/scope rather than by raw file extension alone. Built-in artifact kinds should distinguish page SVG, page PNG, document PDF, document IDML, and document/tree inputs.

Rationale: PDF should be able to accept a PNG page source now and potentially an SVG page source later, but this must be an explicit backend capability, not an accidental string convention.

Alternatives considered:
- Format-only graph (`svg -> png -> pdf`): simpler, but ambiguous for document-scoped outputs and custom named PNG presets.
- Runtime duck typing: easier initially, but validation errors would happen too late and be harder to explain.

### Preset source semantics

Add a `source` field for presets that consume another preset. Defaults should be conservative and built-in:
- SVG page output has no preset source; it is produced from rendered page content.
- PNG defaults to `source="svg"`.
- `pdf()` keeps the existing `pdf` target name and uses the legacy SVG-rendered raster fallback for compatibility.
- `pdf(source="1080p")` still keeps the target name `pdf`, but routes PDF generation through the named PNG page preset for better raster quality.
- Future SVG-sourced PDF work means converting SVG drawing content into equivalent PDF vector/text/image operations. PDF is not literally SVG-in-a-wrapper; it is its own page description format with vector capabilities.
- IDML consumes the document tree and has no page preset source.

Rationale: Users need to express `pdf(source="1080p")` without renaming the common `pdf` target; the system should infer common defaults without hiding important dependency edges.

### Plan before executing

Build should resolve requested targets, expand dependencies transitively, validate the graph, topologically sort nodes, then execute. Cycles and unsupported routes are validation/render planning errors, not backend surprises.

Rationale: The same planner can explain why a target cannot run, show predictable output order, and avoid duplicated intermediate work.

### Intermediate artifact policy

The planner should track intermediate artifacts in memory and/or a spec-local cache. Only explicitly requested terminal targets should be written to the user output directory unless a dependency is also explicitly requested.

Rationale: `folio build pdf` may need `1080p` PNGs, but users should not get extra public PNG files unless they requested `1080p` or `all`.

### Built-in handlers first

Implement built-in step handlers for SVG, PNG, PDF, and IDML with explicit accepted input artifact types. Defer a public plugin API until internal semantics stabilize.

Rationale: The current pain is built-in export quality and reuse. Plugin API design should follow proven internal abstractions.

## Risks / Trade-offs

- [Risk] Hidden behavior changes for existing `pdf()` users → Mitigation: preserve `pdf()` as the legacy SVG-rendered raster route and document its quality limits.
- [Risk] Extra complexity in build command internals → Mitigation: isolate planning/execution in a dedicated module with focused tests.
- [Risk] Intermediate cache invalidation bugs → Mitigation: first implementation can reuse intermediates only within a single process build, then persist later if needed.
- [Risk] Too much API surface too early → Mitigation: expose only `source` and built-in helpers now; keep handler abstractions private.

## Migration Plan

1. Add model/schema support for preset source metadata.
2. Implement graph validation and planning without changing the CLI entrypoint.
3. Move existing SVG/PNG/PDF/IDML execution behind built-in pipeline handlers.
4. Preserve current default target behavior and add source-aware examples.
5. Use `pdf(source="1080p")` in showcase projects once available.

Rollback is straightforward: keep current direct writer path available until the planner is fully covered by tests.

## Open Questions

- Should later true SVG-to-vector-PDF conversion be implemented as `pdf(source="svg")`, a separate backend option, or a separate preset helper?
- Should intermediate PNGs be visible in cache by default, or only retained in memory for the initial implementation?
- What user-facing diagnostics should be exposed for planned dependency graphs (`--dry-run` / `--plan` later)?
