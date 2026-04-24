## Context

The export preset implementation made `pdf()` a first-class document-scoped target, but the first backend only emitted blank PDF pages with correct dimensions. That was useful as a structural placeholder but fails the user expectation that `folio build pdf` produces a visual deliverable matching the rendered Folio pages.

Folio already has a canonical page rendering path (DSL → rendered SVG pages) and an SVG rasterization backend chain (Playwright, CairoSVG, rsvg-convert, Inkscape). The quick fix should reuse those paths rather than inventing a separate PDF drawing engine.

## Goals / Non-Goals

**Goals:**
- Make `pdf()` exports visually populated.
- Preserve the existing public API and CLI: `pdf()`, `folio build pdf`, and `folio build all` remain unchanged.
- Reuse rendered SVG page content as the PDF source of truth.
- Produce one multi-page PDF per document, preserving page order and physical dimensions.
- Fail loudly if rasterization or assembly fails.

**Non-Goals:**
- Designing the general export pipeline graph model.
- Producing editable/selectable text in PDFs.
- Implementing SVG-to-vector-PDF conversion or print profiles.
- Adding new public DSL options for PDF quality, DPI, color profile, bleed, or compression.

## Decisions

1. **Implement PDF as SVG → PNG → PDF for this fix.**
   - Rationale: this gives immediate visual correctness with the raster stack Folio already owns.
   - Alternative considered: keep blank PDFs until the general pipeline engine exists. Rejected because blank PDFs are actively misleading.
   - Alternative considered: SVG → vector PDF. Deferred because backend choice and merge behavior need a separate design.

2. **Pass rendered pages to the PDF writer.**
   - Rationale: the PDF backend needs actual page SVG content, not just the `Document` model.
   - The build command already has `RenderedDocument` values, so the integration point can stay local to document-scoped PDF writing.

3. **Use temporary/intermediate raster files internally.**
   - Rationale: the existing raster helper writes PNG files. Temporary files avoid changing the raster API for this quick fix.
   - The final artifact remains the requested PDF in the output directory.

4. **Use page dimensions from the Folio page model.**
   - Rationale: generated PNGs may have pixel dimensions, but PDF page physical size should match authored page size in millimeters.
   - If the image-to-PDF assembly path cannot encode physical size precisely, tests should at least validate pixel content and page count; a future vector/pipeline change can improve print semantics.

## Risks / Trade-offs

- **Risk: Raster PDFs lose editable/selectable text.** → Mitigation: document this as the quick backend and defer vector PDF to `add-export-pipelines`.
- **Risk: PDF output depends on raster backend availability.** → Mitigation: reuse the same failure diagnostics as PNG export presets.
- **Risk: Large 4k-like page rasters can increase PDF size.** → Mitigation: use a reasonable internal viewport derived from page SVG dimensions for now; expose quality controls later only through the pipeline change.
- **Risk: Visual fidelity may differ across raster backends.** → Mitigation: this is already true for PNG exports; tests should assert populated output and dimensions rather than exact pixels.

## Migration Plan

1. Change the PDF writer API to accept rendered pages or a rendered document.
2. Rasterize each rendered SVG page into a temporary PNG using existing viewport derivation.
3. Assemble the PNGs into a multi-page PDF.
4. Update build command integration for `ExportFormat.PDF`.
5. Add tests that catch blank output regressions.

Rollback strategy: revert the PDF writer and build integration to the previous structural writer if raster-backed PDFs cause unexpected runtime failures.

## Open Questions

- Which raster viewport should be used for print-oriented A4 PDFs before the general pipeline API exists?
- Should the quick backend require Pillow explicitly, or report a clear infrastructure error if image-to-PDF assembly support is unavailable?
