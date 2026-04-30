# `folio.interfaces` — Protocol Interface Definitions

## Responsibility

Defines the **structural contracts** between Folio engine subsystems using Python Protocols. These protocols enable loose coupling: any class satisfying the interface works with the engine without requiring inheritance. The layer provides four contracts:

1. **Builder** — orchestrates the full build pipeline
2. **Renderer** — converts Document model to SVG pages
3. **Exporter** — writes rendered output to file formats (PDF, IDML, PNG)
4. **SearchProvider** — searches for stock images or SVG assets

## Design

### Protocol Pattern
- Uses `typing.Protocol` with `@runtime_checkable` for structural subtyping
- Existing classes satisfy protocols without explicit inheritance
- Located in `__init__.py` for clean public API surface

### Abstractions

| Protocol | Input | Output | Key Method |
|----------|-------|--------|------------|
| `Builder` | `spec_path: Path` | `BuildResult` | `build(...)` |
| `Renderer` | `Document` | `BuildResult` | `render_document(...)`, `validate_document(...)` |
| `Exporter` | `RenderedDocument` | `list[Path]` | `execute_export_plan(...)` |
| `SearchProvider` | `query: str` | `list[object]` | `search(...)` |

### Data Models (from `folio.core.model`)
- `Document` — in-memory model with Element trees
- `BuildResult` — contains rendered pages and export artifacts
- `RenderedDocument` — document with SVG page content

## Flow

```
User/DSL → Builder.build(spec_path, ...)
    │
    ├── [load spec] → Document model
    │
    ├── Renderer.validate_document(Document)
    │       └── raises on structural errors
    │
    ├── Renderer.render_document(Document, config_dir, source_path)
    │       └── returns BuildResult (SVG pages)
    │
    ├── [resolve targets] → ExportPlan objects
    │
    ├── Exporter.execute_export_plan(RenderedDocument, plan, out_dir)
    │       └── returns list[Path] of written artifacts
    │
    └── [optional] SearchProvider.search(query, limit)
            └── used for stock image/SVG asset lookup
```

## Integration

### Dependencies
- **`folio.core.model`** — imports `BuildResult`, `Document`, `RenderedDocument`
- **`pathlib.Path`** — file path handling across all protocols

### Consumers
- **CLI entry point** (`folio.cli.app`) — uses Builder to run builds
- **Engine implementations** — must implement all four protocols
- **Test infrastructure** — uses `@runtime_checkable` for interface verification

### Exported API
```python
from folio.interfaces import Builder, Exporter, Renderer, SearchProvider
```

### Constraints
- Circular import avoidance: `Exporter.execute_export_plan` accepts `plan: object` instead of `ExportPlan` type
- `SearchProvider.search` returns `list[object]` (provider-specific result shape)
