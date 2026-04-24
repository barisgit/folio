## 1. Model and Validation

- [ ] 1.1 Add source/dependency metadata to export preset model and built-in helper functions.
- [ ] 1.2 Validate source references, source scope, artifact type compatibility, and dependency cycles.
- [ ] 1.3 Add tests for unknown sources, unsupported routes, and cycle diagnostics.

## 2. Planning Core

- [ ] 2.1 Introduce an export pipeline planner that resolves requested targets plus transitive dependencies.
- [ ] 2.2 Represent planned steps with typed input/output artifact metadata and page/document scope.
- [ ] 2.3 Implement deterministic topological ordering and duplicate dependency coalescing.
- [ ] 2.4 Add focused planner tests for shared dependencies, transitive dependencies, and ordering.

## 3. Built-in Pipeline Execution

- [ ] 3.1 Move SVG page writing behind a built-in pipeline step.
- [ ] 3.2 Move PNG rasterization behind a built-in pipeline step that consumes SVG page artifacts.
- [ ] 3.3 Update PDF export to consume planned page artifacts, especially PNG sources such as `1080p`.
- [ ] 3.4 Keep IDML as a document-scoped built-in step that consumes the document tree.
- [ ] 3.5 Ensure dependency artifacts are reused within one build and only public outputs are written to `out/`.

## 4. Build CLI Integration

- [ ] 4.1 Replace direct target execution in `folio build` with plan creation plus execution.
- [ ] 4.2 Preserve existing CLI behavior for defaults, explicit targets, `all`, `--page`, `--out-dir`, and `--no-cache`.
- [ ] 4.3 Improve build errors to name the requested target and failing dependency step.
- [ ] 4.4 Add CLI tests for `pdf(source="1080p")`, implicit dependency execution, and no unrequested PNG outputs.

## 5. Docs and Verification

- [ ] 5.1 Document pipeline/source examples in the README and Folio skill docs.
- [ ] 5.2 Update the TM42 brochure showcase to use a source-backed PDF preset.
- [ ] 5.3 Run focused export pipeline tests.
- [ ] 5.4 Run the full project test suite, lint, and OpenSpec validation.
