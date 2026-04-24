## Why

The initial `pdf()` export backend writes a structurally valid but visually blank PDF, which makes PDF targets unusable for real deliverables. Folio already has reliable SVG rendering and PNG rasterization, so the quickest fix is to make PDF export consume rendered page output instead of emitting empty placeholder pages.

## What Changes

- Change the `pdf` export target from a blank document writer to a visual PDF writer.
- Render each participating document page through Folio's existing SVG output path and rasterization backend.
- Assemble the rasterized page images into a multi-page PDF artifact with page order and physical dimensions preserved.
- Keep the public DSL and CLI unchanged: users still declare `pdf()` and run `folio build pdf` or `folio build all`.
- Report PDF export failures as build/render errors instead of silently producing blank or partial PDFs.

## Capabilities

### New Capabilities

### Modified Capabilities
- `export-presets`: PDF document-scoped exports must produce visually populated PDF pages derived from rendered Folio pages, not blank placeholder pages.

## Impact

- Affected export backend: `src/folio/export/pdf.py`.
- Affected build integration: `src/folio/commands/build.py` may need to pass rendered page content to the PDF writer.
- Affected dependencies: implementation may use existing rasterization backends plus Pillow image-to-PDF support already available in Folio workflows.
- Affected tests/docs: PDF target tests should verify non-empty visual output, page count, page size, and failure behavior; docs should clarify that the quick PDF backend is raster-backed.
