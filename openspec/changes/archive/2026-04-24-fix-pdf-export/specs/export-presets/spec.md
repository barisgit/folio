## MODIFIED Requirements

### Requirement: Document-scoped export outputs
Folio SHALL write one artifact per document for document-scoped presets.

#### Scenario: IDML preset output
- **WHEN** Folio builds the `idml` preset
- **THEN** it packages the whole document as an IDML artifact
- **AND** writes the IDML file to the resolved output directory

#### Scenario: PDF preset output
- **WHEN** Folio builds the `pdf` preset
- **THEN** it exports the whole document as a PDF artifact
- **AND** the PDF pages visually contain the rendered Folio page output
- **AND** writes the PDF file to the resolved output directory

#### Scenario: PDF page order and count
- **WHEN** Folio builds the `pdf` preset for a document with multiple pages
- **THEN** the PDF contains one page for each document page
- **AND** orders PDF pages by Folio page order

#### Scenario: PDF export failure
- **WHEN** Folio cannot rasterize or assemble one or more pages needed for a PDF preset
- **THEN** it reports a build/render error for the PDF target
- **AND** does not silently emit a blank, partial, or misleading PDF artifact

#### Scenario: Document artifact naming
- **WHEN** a document declares a name or filename stem
- **THEN** document-scoped exports use that stem by default
- **AND** otherwise fall back to Folio's existing document artifact naming behavior
