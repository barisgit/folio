## 1. Model and Validation

- [x] 1.1 Add source/dependency metadata to export preset model and built-in helper functions.
- [x] 1.2 Validate source references, source scope, artifact type compatibility, and dependency cycles.
- [x] 1.3 Preserve `pdf()` as the legacy SVG-rendered raster fallback and support `pdf(source="1080p")` without renaming the `pdf` target.
- [x] 1.4 Add tests for unknown sources, unsupported routes, cycle diagnostics, and source compatibility rules.

## 2. Planning Core

- [x] 2.1 Introduce an export pipeline planner that resolves requested targets plus transitive dependencies.
- [x] 2.2 Represent planned steps with typed input/output artifact metadata and page/document scope.
- [x] 2.3 Define artifact kinds for page SVG, page PNG, document PDF, document IDML, and document tree inputs.
- [x] 2.4 Implement deterministic topological ordering and duplicate dependency coalescing.
- [x] 2.5 Add focused planner tests for shared dependencies, transitive dependencies, and ordering.

## 3. Built-in Pipeline Execution

- [x] 3.1 Move SVG page writing behind a built-in pipeline step.
- [x] 3.2 Move PNG rasterization behind a built-in pipeline step that consumes SVG page artifacts.
- [x] 3.3 Update PDF export to consume planned page artifacts, especially PNG sources such as `1080p`.
- [x] 3.4 Add a PDF page input abstraction that can represent PNG-backed pages now and future SVG-to-vector-PDF inputs later.
- [x] 3.5 Keep IDML as a document-scoped built-in step that consumes the document tree.
- [x] 3.6 Ensure dependency artifacts are reused within one build and only public outputs are written to `out/`.

## 4. Build CLI Integration

- [x] 4.1 Replace direct target execution in `folio build` with plan creation plus execution.
- [x] 4.2 Preserve existing CLI behavior for defaults, explicit targets, `all`, `--page`, `--out-dir`, and `--no-cache`.
- [x] 4.3 Improve build errors to name the requested target and failing dependency step.
- [x] 4.4 Add CLI tests for `pdf(source="1080p")`, implicit dependency execution, and no unrequested PNG outputs.

## 5. Docs and Verification

- [x] 5.1 Document pipeline/source examples in the README and Folio skill docs.
- [x] 5.2 Update the TM42 brochure showcase to use a source-backed PDF preset.
- [x] 5.3 Run focused export pipeline tests.
- [x] 5.4 Run the full project test suite, lint, and OpenSpec validation.
