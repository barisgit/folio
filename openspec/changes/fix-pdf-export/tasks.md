## 1. PDF Writer

- [ ] 1.1 Refactor `src/folio/export/pdf.py` so PDF writing accepts rendered page SVG content plus page metadata instead of only a bare `Document`.
- [ ] 1.2 Rasterize each rendered SVG page through the existing SVG-to-PNG backend chain into temporary/intermediate PNG files.
- [ ] 1.3 Assemble rasterized page images into one multi-page PDF artifact in document page order.
- [ ] 1.4 Preserve document artifact naming and resolved output directory behavior for `pdf()` targets.
- [ ] 1.5 Surface rasterization or PDF assembly failures as build/render errors without leaving blank or partial PDFs behind.

## 2. Build Integration

- [ ] 2.1 Update `src/folio/commands/build.py` so `ExportFormat.PDF` passes the `RenderedDocument` page content needed by the PDF writer.
- [ ] 2.2 Keep the public DSL/CLI unchanged: `pdf()`, `folio build pdf`, default document-scoped exports, and `folio build all` continue to resolve through export presets.
- [ ] 2.3 Ensure multi-document builds produce one populated PDF per document.

## 3. Tests

- [ ] 3.1 Add PDF export tests that detect blank placeholder regressions by verifying generated PDFs contain page image/content data.
- [ ] 3.2 Add tests for PDF page count and page order for multi-page documents.
- [ ] 3.3 Add tests for PDF export failure behavior when rasterization fails.
- [ ] 3.4 Update existing CLI/build tests that expected only structural PDF output.

## 4. Docs and Verification

- [ ] 4.1 Document that the quick PDF backend is raster-backed and visually matches rendered pages, while editable/vector PDF is deferred to the export pipeline change.
- [ ] 4.2 Run focused PDF/build tests.
- [ ] 4.3 Run the full project test suite, lint, and OpenSpec validation.
- [ ] 4.4 Rebuild the TM42 brochure PDF showcase and verify it is no longer blank.
