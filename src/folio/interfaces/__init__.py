"""Folio engine protocol interfaces.

Protocols define the contracts between engine subsystems.
They use structural subtyping — existing classes satisfy them without inheritance.
"""

from folio.interfaces.builder import Builder
from folio.interfaces.exporter import Exporter
from folio.interfaces.renderer import Renderer
from folio.interfaces.search import SearchProvider

__all__ = [
    "Builder",
    "Exporter",
    "Renderer",
    "SearchProvider",
]
