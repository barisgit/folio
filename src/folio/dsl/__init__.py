"""Folio DSL — public API facade.

This package re-exports the public DSL from folio.core.dsl. All
implementation lives in core/; dsl/ contains only re-exports.

Users import from this package:
    from folio.dsl import rect, text, page, document, collection
"""

from __future__ import annotations

from folio.core.dsl import *  # noqa: F401,F403
from folio.core.dsl import __all__ as _core_all

__all__ = _core_all
