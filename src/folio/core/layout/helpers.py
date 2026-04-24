from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Columns:
    start_mm: float
    column_width_mm: float
    count: int
    gap_mm: float = 0.0

    @classmethod
    def from_bounds(
        cls,
        *,
        start_mm: float,
        width_mm: float,
        count: int,
        gap_mm: float = 0.0,
    ) -> Columns:
        if count <= 0:
            raise ValueError("count must be positive")
        column_width_mm = (width_mm - ((count - 1) * gap_mm)) / count
        if column_width_mm <= 0:
            raise ValueError("column width must be positive")
        return cls(
            start_mm=start_mm,
            column_width_mm=column_width_mm,
            count=count,
            gap_mm=gap_mm,
        )

    @classmethod
    def from_inside(
        cls,
        *,
        inside: tuple[float, float],
        count: int,
        gap_mm: float = 0.0,
    ) -> Columns:
        left_mm, right_mm = inside
        return cls.from_bounds(
            start_mm=left_mm,
            width_mm=right_mm - left_mm,
            count=count,
            gap_mm=gap_mm,
        )

    def x(self, index: int) -> float:
        if index < 1 or index > self.count:
            raise ValueError(f"column index out of range: {index}")
        return self.start_mm + ((index - 1) * (self.column_width_mm + self.gap_mm))

    def bounds(self, index: int) -> tuple[float, float]:
        return (self.x(index), self.column_width_mm)


@dataclass(frozen=True)
class Grid:
    origin_x_mm: float
    origin_y_mm: float
    columns: int
    cell_width_mm: float
    cell_height_mm: float
    column_gap_mm: float = 0.0
    row_gap_mm: float = 0.0
    rows: int | None = None

    @classmethod
    def from_bounds(
        cls,
        *,
        x_mm: float,
        y_mm: float,
        width_mm: float,
        columns: int,
        cell_height_mm: float,
        column_gap_mm: float = 0.0,
        row_gap_mm: float = 0.0,
    ) -> Grid:
        if columns <= 0:
            raise ValueError("columns must be positive")
        cell_width_mm = (width_mm - ((columns - 1) * column_gap_mm)) / columns
        if cell_width_mm <= 0:
            raise ValueError("cell width must be positive")
        return cls(
            origin_x_mm=x_mm,
            origin_y_mm=y_mm,
            columns=columns,
            cell_width_mm=cell_width_mm,
            cell_height_mm=cell_height_mm,
            column_gap_mm=column_gap_mm,
            row_gap_mm=row_gap_mm,
        )

    @classmethod
    def from_inside(
        cls,
        *,
        inside: tuple[float, float, float, float],
        columns: int,
        rows: int,
        column_gap_mm: float = 0.0,
        row_gap_mm: float = 0.0,
    ) -> Grid:
        if rows <= 0:
            raise ValueError("rows must be positive")
        x_mm, y_mm, width_mm, height_mm = inside
        cell_height_mm = (height_mm - ((rows - 1) * row_gap_mm)) / rows
        if cell_height_mm <= 0:
            raise ValueError("cell height must be positive")
        base = Grid.from_bounds(
            x_mm=x_mm,
            y_mm=y_mm,
            width_mm=width_mm,
            columns=columns,
            cell_height_mm=cell_height_mm,
            column_gap_mm=column_gap_mm,
            row_gap_mm=row_gap_mm,
        )
        return cls(
            origin_x_mm=base.origin_x_mm,
            origin_y_mm=base.origin_y_mm,
            columns=base.columns,
            cell_width_mm=base.cell_width_mm,
            cell_height_mm=base.cell_height_mm,
            column_gap_mm=base.column_gap_mm,
            row_gap_mm=base.row_gap_mm,
            rows=rows,
        )

    def cell_origin(self, index: int) -> tuple[float, float]:
        if index < 1:
            raise ValueError(f"grid index must be positive: {index}")
        zero_based = index - 1
        column = zero_based % self.columns
        row = zero_based // self.columns
        return (
            self.origin_x_mm + (column * (self.cell_width_mm + self.column_gap_mm)),
            self.origin_y_mm + (row * (self.cell_height_mm + self.row_gap_mm)),
        )

    def cell_bounds(self, index: int) -> tuple[float, float, float, float]:
        x_mm, y_mm = self.cell_origin(index)
        return (x_mm, y_mm, self.cell_width_mm, self.cell_height_mm)


@dataclass(frozen=True)
class FlowColumns:
    origin_x_mm: float
    origin_y_mm: float
    count: int
    width_mm: float
    column_width_mm: float
    gap_mm: float = 0.0
    arrow_width_mm: float = 0.0

    @classmethod
    def from_inside(
        cls,
        *,
        inside: tuple[float, float, float],
        count: int,
        gap_mm: float = 0.0,
        arrow_width_mm: float = 0.0,
    ) -> FlowColumns:
        if count <= 0:
            raise ValueError("count must be positive")
        x_mm, y_mm, width_mm = inside
        column_width_mm = (
            width_mm - ((count - 1) * arrow_width_mm) - (2 * (count - 1) * gap_mm)
        ) / count
        if column_width_mm <= 0:
            raise ValueError("flow column width must be positive")
        return cls(
            origin_x_mm=x_mm,
            origin_y_mm=y_mm,
            count=count,
            width_mm=width_mm,
            column_width_mm=column_width_mm,
            gap_mm=gap_mm,
            arrow_width_mm=arrow_width_mm,
        )

    def panel_x(self, index: int) -> float:
        if index < 1 or index > self.count:
            raise ValueError(f"panel index out of range: {index}")
        step_mm = self.column_width_mm + self.arrow_width_mm + (2 * self.gap_mm)
        return self.origin_x_mm + ((index - 1) * step_mm)

    def panel_bounds(self, index: int, height_mm: float) -> tuple[float, float, float, float]:
        return (self.panel_x(index), self.origin_y_mm, self.column_width_mm, height_mm)

    def arrow_x(self, index: int) -> float:
        if index < 1 or index >= self.count:
            raise ValueError(f"arrow index out of range: {index}")
        return self.panel_x(index) + self.column_width_mm + self.gap_mm

    def arrow_center_x(self, index: int) -> float:
        return self.arrow_x(index) + (self.arrow_width_mm / 2.0)


def cols(n: int, *, inside: tuple[float, float], gap: float = 0.0) -> Columns:
    """Create ``n`` equal-width columns inside a bounding box.

    Args:
        n: Number of columns.
        inside: Bounding box as ``(width, height)`` in mm.
        gap: Gap between columns in mm.

    Returns:
        Columns layout helper with ``.widths`` and ``.x_offsets``.
    """
    return Columns.from_inside(inside=inside, count=n, gap_mm=gap)


def grid(
    cols: int,
    rows: int,
    *,
    inside: tuple[float, float, float, float],
    col_gap: float = 0.0,
    row_gap: float = 0.0,
) -> Grid:
    """Create a grid layout inside a bounding box.

    Args:
        cols: Number of columns.
        rows: Number of rows.
        inside: Bounding box as ``(x, y, width, height)`` in mm.
        col_gap: Gap between columns in mm.
        row_gap: Gap between rows in mm.

    Returns:
        Grid layout helper with ``.cell(row, col)`` and ``.cells``.
    """
    return Grid.from_inside(
        inside=inside,
        columns=cols,
        rows=rows,
        column_gap_mm=col_gap,
        row_gap_mm=row_gap,
    )


def flow_cols(
    n: int = 3,
    *,
    inside: tuple[float, float, float],
    gap: float = 0.0,
    arrow_w: float = 0.0,
) -> FlowColumns:
    """Create ``n`` flow-style columns with arrow indicators.

    Args:
        n: Number of columns.
        inside: Bounding box as ``(x, y, width)`` in mm.
        gap: Gap between columns in mm.
        arrow_w: Arrow indicator width in mm.

    Returns:
        FlowColumns layout helper with ``.columns`` positions.
    """
    return FlowColumns.from_inside(
        inside=inside,
        count=n,
        gap_mm=gap,
        arrow_width_mm=arrow_w,
    )
