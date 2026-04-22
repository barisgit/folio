from __future__ import annotations

from folio.layout import Columns, FlowColumns, Grid, cols, flow_cols, grid


def test_columns_from_bounds_returns_even_positions() -> None:
    columns = Columns.from_bounds(start_mm=16, width_mm=178, count=3, gap_mm=7)

    assert round(columns.column_width_mm, 6) == round((178 - 14) / 3, 6)
    assert columns.x(1) == 16
    assert round(columns.x(2), 6) == round(16 + columns.column_width_mm + 7, 6)
    assert round(columns.x(3), 6) == round(16 + (2 * (columns.column_width_mm + 7)), 6)


def test_grid_from_bounds_returns_cell_origins() -> None:
    layout = Grid.from_bounds(
        x_mm=16,
        y_mm=141,
        width_mm=178,
        columns=4,
        cell_height_mm=16.5,
        column_gap_mm=2,
        row_gap_mm=2,
    )

    assert round(layout.cell_width_mm, 6) == round((178 - 6) / 4, 6)
    assert layout.cell_origin(1) == (16, 141)
    assert layout.cell_origin(4) == (
        16 + (3 * (layout.cell_width_mm + 2)),
        141,
    )
    assert layout.cell_origin(5) == (16, 141 + 16.5 + 2)


def test_cols_helper_matches_columns_from_inside() -> None:
    layout = cols(3, inside=(16, 194), gap=7)

    assert isinstance(layout, Columns)
    assert layout.bounds(2) == (layout.x(2), layout.column_width_mm)
    assert round(layout.column_width_mm, 6) == round((178 - 14) / 3, 6)


def test_grid_helper_computes_cell_height_from_inside() -> None:
    layout = grid(4, 2, inside=(16, 141, 178, 35), col_gap=2, row_gap=2)

    assert isinstance(layout, Grid)
    assert layout.rows == 2
    assert round(layout.cell_width_mm, 6) == round((178 - 6) / 4, 6)
    assert layout.cell_height_mm == 16.5
    assert layout.cell_bounds(5) == (16, 159.5, layout.cell_width_mm, 16.5)


def test_flow_cols_helper_accounts_for_arrows_and_gaps() -> None:
    layout = flow_cols(inside=(16, 52, 178), gap=2, arrow_w=5)

    assert isinstance(layout, FlowColumns)
    assert round(layout.column_width_mm, 6) == round((178 - 10 - 8) / 3, 6)
    assert layout.panel_bounds(2, 78) == (
        layout.panel_x(2),
        52,
        layout.column_width_mm,
        78,
    )
    assert layout.arrow_x(1) == layout.panel_x(1) + layout.column_width_mm + 2
    assert layout.arrow_center_x(2) == layout.arrow_x(2) + 2.5
