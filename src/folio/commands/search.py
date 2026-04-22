"""Compatibility wrapper for the ``folio.commands.search`` package implementation."""

from folio.commands.search import (
    app,
    fetch_stock,
    search_app,
    search_svg_assets,
    stock_command,
    svg_command,
)

__all__ = ["app", "fetch_stock", "search_app", "search_svg_assets", "stock_command", "svg_command"]
