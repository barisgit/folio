"""Folio DSL documentation index.

The package owns the JSON index that describes every public DSL symbol. The
index is generated from the DSL source, committed at `index.json`, shipped
with the wheel, and consumed at runtime by the `folio docs` CLI.

Regenerate the index with `python -m folio.docs.generate` or the equivalent
`folio docs generate` CLI alias.
"""

from __future__ import annotations

from folio.docs.schema import (
    VALID_KINDS,
    Example,
    Index,
    Param,
    Returns,
    Symbol,
)

__all__ = [
    "Example",
    "Index",
    "Param",
    "Returns",
    "Symbol",
    "VALID_KINDS",
]
