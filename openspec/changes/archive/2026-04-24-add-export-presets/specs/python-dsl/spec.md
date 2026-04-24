## ADDED Requirements

### Requirement: Export preset authoring fields
Folio SHALL expose document and page fields for declaring export presets, default exports, and page extra exports in Python specs.

#### Scenario: Document declares export presets
- **WHEN** a Python spec creates a `Document` with `export_presets=[svg(), idml(), pdf(), png("1080p", viewport=(1920, 1080))]`
- **THEN** Folio stores those presets on the document model
- **AND** makes the preset names available to validation and build target resolution

#### Scenario: Document declares default exports
- **WHEN** a Python spec creates a `Document` with `default_exports=["svg"]`
- **THEN** Folio stores that default export list on the document model
- **AND** uses it as the default target set for `folio build`

#### Scenario: Page declares extra exports
- **WHEN** a Python spec creates a page with `extra_exports=["1080p", "4k"]`
- **THEN** Folio stores those extra export references on the page model
- **AND** uses them to decide page participation for non-default page-scoped presets

#### Scenario: Export helper functions are available
- **WHEN** a user imports from `folio.dsl`
- **THEN** the user can access `svg`, `png`, `pdf`, and `idml` export preset helper functions
- **AND** each helper returns a value accepted by `Document(export_presets=[...])`

### Requirement: Export preset validation in DSL documents
Folio SHALL validate export preset declarations and references as part of document validation.

#### Scenario: Duplicate preset names
- **WHEN** a document contains multiple export presets with the same name
- **THEN** Folio rejects the document with a validation error
- **AND** includes the duplicate preset name in the diagnostic

#### Scenario: Unknown default export
- **WHEN** `default_exports` references a preset that is not declared by the document
- **THEN** Folio rejects the document with a validation error
- **AND** includes the unknown preset name in the diagnostic

#### Scenario: Unknown page extra export
- **WHEN** a page `extra_exports` entry references a preset that is not declared by the document
- **THEN** Folio rejects the document with a validation error
- **AND** includes the page id or page number and unknown preset name in the diagnostic

#### Scenario: Page references document-scoped preset
- **WHEN** a page `extra_exports` entry references a document-scoped preset such as `pdf` or `idml`
- **THEN** Folio rejects the document with a validation error
- **AND** explains that `extra_exports` accepts only page-scoped presets
