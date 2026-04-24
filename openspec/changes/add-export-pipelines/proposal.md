## Why

Export targets are no longer always one-step writers: a useful PDF may depend on SVG pages and PNG rasterization, while future deliverables may reuse the same intermediate artifacts in different combinations. Folio needs an explicit export pipeline model so targets can declare dependencies and execute repeatable multi-step build graphs instead of hiding ad-hoc chains inside each writer.

## What Changes

- Introduce export pipeline semantics for preset targets, where a target can depend on intermediate outputs such as rendered SVG pages or rasterized PNG pages.
- Model build execution as target resolution plus dependency planning plus step execution.
- Let presets express or infer their source pipeline, for example `png` from SVG, screen PDF from PNG, print PDF from SVG/PDF conversion, and IDML from the DSL document tree.
- Reuse/capture intermediate artifacts deterministically so `folio build pdf` can build required prerequisites without requiring users to run `folio build svg` first.
- Keep the first design focused on Folio-owned built-in pipelines before introducing third-party plugin APIs.

## Capabilities

### New Capabilities
- `export-pipelines`: Defines dependency-aware export target planning and execution for multi-step built-in export workflows.

### Modified Capabilities
- `export-presets`: Export presets gain source/dependency semantics and can be executed as pipelines rather than only direct artifact writers.
- `build-and-validate`: Build command execution plans and runs target dependencies while preserving target-based CLI behavior.

## Impact

- Affected DSL/API: export preset model may gain source, dependency, or pipeline fields.
- Affected build internals: target resolution, cache/intermediate artifact handling, output ordering, and error reporting.
- Affected export backends: PNG, PDF, SVG, and IDML become explicit pipeline steps or terminal writers.
- Affected tests/docs: pipeline planning, dependency execution, intermediate reuse, failure propagation, and user-facing examples need coverage.
