from __future__ import annotations

import os
from collections.abc import Callable
from hashlib import sha256
from pathlib import Path
from typing import TYPE_CHECKING, Any

from folio.dsl import builtins as _builtins
from folio.dsl.model import Element

if TYPE_CHECKING:
    from matplotlib.axes import Axes
    from matplotlib.figure import Figure

_MM_PER_INCH = 25.4
_DEFAULT_CACHE_DIRNAME = ".folio-cache"
_CACHE_ENV_VAR = "FOLIO_CHART_CACHE_DIR"
_spec_base_dir: Path | None = None


def set_spec_base_dir(path: Path | None) -> None:
    """Set the base directory for resolving chart cache paths.

    The loader calls this before executing a spec module so charts land
    next to the spec instead of the user's current working directory.
    """
    global _spec_base_dir
    _spec_base_dir = Path(path).expanduser().resolve() if path is not None else None


def _resolve_cache_dir(override: Path | None) -> Path:
    if override is not None:
        return Path(override).expanduser().resolve()
    env_override = os.environ.get(_CACHE_ENV_VAR)
    if env_override:
        return Path(env_override).expanduser().resolve()
    base = _spec_base_dir if _spec_base_dir is not None else Path.cwd()
    return (base / _DEFAULT_CACHE_DIRNAME / "charts").resolve()


def _import_matplotlib() -> Any:
    try:
        import matplotlib
    except ImportError as exc:
        raise RuntimeError(
            "chart() requires matplotlib. Install with `pip install matplotlib` "
            "(optional dependency — folio does not require it for other primitives)."
        ) from exc
    matplotlib.use("Agg", force=False)
    import matplotlib.pyplot as plt

    return plt


def _figure_to_png_bytes(fig: Figure, *, dpi: int, transparent: bool) -> bytes:
    from io import BytesIO

    buffer = BytesIO()
    fig.savefig(
        buffer,
        format="png",
        dpi=dpi,
        transparent=transparent,
        bbox_inches=None,
        pad_inches=0,
    )
    return buffer.getvalue()


class ChartHandle:
    """Render a matplotlib figure into a folio Element as a cached PNG.

    Usage — decorator form (preferred for single-block charts):

        @chart("revenue", x_mm=20, y_mm=120, width_mm=80, height_mm=40)
        def revenue(ax):
            ax.plot(months, values)
        # revenue is now an Element

    Usage — context manager form (when you want the figure object too):

        ch = chart("trends", x_mm=20, y_mm=120, width_mm=80, height_mm=40)
        with ch as ax:
            ax.plot(...)
        page(ch.element, ...)
    """

    __slots__ = (
        "_cache_dir",
        "_dpi",
        "_element",
        "_element_id",
        "_fig",
        "_figure_kwargs",
        "_height_mm",
        "_image_attrs",
        "_plt",
        "_transparent",
        "_width_mm",
        "_x_mm",
        "_y_mm",
    )

    def __init__(
        self,
        element_id: str,
        *,
        x_mm: float,
        y_mm: float,
        width_mm: float,
        height_mm: float,
        dpi: int,
        transparent: bool,
        cache_dir: Path | None,
        figure_kwargs: dict[str, Any],
        image_attrs: dict[str, Any],
    ) -> None:
        if not element_id:
            raise TypeError("chart() requires a non-empty element_id")
        if width_mm <= 0 or height_mm <= 0:
            raise TypeError("chart() width_mm and height_mm must be positive")
        if dpi <= 0:
            raise TypeError("chart() dpi must be positive")
        self._element_id = element_id
        self._x_mm = float(x_mm)
        self._y_mm = float(y_mm)
        self._width_mm = float(width_mm)
        self._height_mm = float(height_mm)
        self._dpi = int(dpi)
        self._transparent = bool(transparent)
        self._cache_dir = _resolve_cache_dir(cache_dir)
        self._figure_kwargs = dict(figure_kwargs)
        self._image_attrs = dict(image_attrs)
        self._plt: Any = None
        self._fig: Figure | None = None
        self._element: Element | None = None

    @property
    def element(self) -> Element:
        if self._element is None:
            raise RuntimeError(
                f"chart('{self._element_id}') has no element yet — "
                "use it as a decorator or enter the with-block before reading .element"
            )
        return self._element

    @property
    def figure(self) -> Figure:
        if self._fig is None:
            raise RuntimeError(
                f"chart('{self._element_id}') has no active figure — "
                "access .figure inside the with-block"
            )
        return self._fig

    def __enter__(self) -> Axes:
        plt = _import_matplotlib()
        self._plt = plt
        width_in = self._width_mm / _MM_PER_INCH
        height_in = self._height_mm / _MM_PER_INCH
        fig = plt.figure(figsize=(width_in, height_in), dpi=self._dpi, **self._figure_kwargs)
        ax = fig.add_subplot(111)
        if self._transparent:
            fig.patch.set_alpha(0.0)
            ax.patch.set_alpha(0.0)
        self._fig = fig
        return ax

    def __exit__(self, exc_type: type[BaseException] | None, *_: Any) -> None:
        fig = self._fig
        plt = self._plt
        try:
            if exc_type is not None or fig is None:
                return
            png_bytes = _figure_to_png_bytes(
                fig, dpi=self._dpi, transparent=self._transparent
            )
            digest = sha256(png_bytes).hexdigest()[:16]
            self._cache_dir.mkdir(parents=True, exist_ok=True)
            png_path = self._cache_dir / f"{self._element_id}-{digest}.png"
            if not png_path.exists():
                png_path.write_bytes(png_bytes)
            reference = self._relative_reference(png_path)
            self._element = _builtins.image(
                self._element_id,
                reference,
                self._x_mm,
                self._y_mm,
                self._width_mm,
                self._height_mm,
                **self._image_attrs,
            )
        finally:
            if fig is not None and plt is not None:
                plt.close(fig)
            self._fig = None
            self._plt = None

    def __call__(self, render: Callable[[Axes], None]) -> Element:
        if not callable(render):
            raise TypeError("chart() decorator target must be callable (render function)")
        with self as ax:
            render(ax)
        return self.element

    @staticmethod
    def _relative_reference(png_path: Path) -> str:
        try:
            return str(png_path.relative_to(Path.cwd()))
        except ValueError:
            return str(png_path)


def chart(
    element_id: str,
    *,
    x_mm: float,
    y_mm: float,
    width_mm: float,
    height_mm: float,
    dpi: int = 300,
    transparent: bool = True,
    cache_dir: Path | None = None,
    figure_kwargs: dict[str, Any] | None = None,
    **image_attrs: Any,
) -> ChartHandle:
    return ChartHandle(
        element_id,
        x_mm=x_mm,
        y_mm=y_mm,
        width_mm=width_mm,
        height_mm=height_mm,
        dpi=dpi,
        transparent=transparent,
        cache_dir=cache_dir,
        figure_kwargs=figure_kwargs or {},
        image_attrs=image_attrs,
    )


__all__ = ["ChartHandle", "chart"]
