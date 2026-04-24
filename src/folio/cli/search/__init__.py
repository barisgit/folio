"""`folio search` command group — thin IO adapter."""
from __future__ import annotations

import typer

from folio.cli.search.stock import fetch_stock, fetch_stock_multi, stock_command
from folio.cli.search.svg import search_svg_assets, svg_command

search_app = typer.Typer(
    name="search",
    help="Search for stock images and SVG assets.",
    no_args_is_help=True,
    rich_markup_mode="rich",
)
app = search_app

search_app.command("stock")(stock_command)
search_app.command("svg")(svg_command)

__all__ = [
    "app",
    "fetch_stock",
    "fetch_stock_multi",
    "search_app",
    "search_svg_assets",
    "stock_command",
    "svg_command",
]
