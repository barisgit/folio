"""Composition functions — page, document, collection, render.

Re-exported from builtins for organizational clarity. The split boundary
may be refined later; for now all element factories and composition functions
live in builtins.py.
"""

from folio.core.dsl.builtins import (
    block,
    collection,
    document,
    page,
    render,
)

__all__ = ["block", "collection", "document", "page", "render"]
