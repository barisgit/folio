"""Matplotlib-backed chart primitive.

A chart renders a matplotlib ``Figure`` to a cached PNG and wraps it as a
folio ``Element`` (kind ``IMAGE``) that participates in the normal layout,
reconcile, and SVG-embedding pipeline.

Three usage shapes share one code path:

    # 1. Decorator — the common case. The function receives an Axes.
    @chart("revenue", x_mm=20, y_mm=120, width_mm=80, height_mm=40)
    def revenue(ax):
        ax.plot(months, values)
    # revenue is now an Element

    # 2. Context manager — when you want the Figure object alongside the Axes.
    handle = chart("trends", x_mm=20, y_mm=120, width_mm=80, height_mm=40)
    with handle as ax:
        ax.plot(...)
    element = handle.element

    # 3. Pre-built Figure — for libraries (seaborn, pandas) that hand back
    # a Figure you constructed yourself. The Figure is not closed for you.
    fig = sns.lineplot(data=df).figure
    element = chart("revenue", x_mm=20, y_mm=120, width_mm=80, height_mm=40).from_figure(fig)

Rendered PNGs are content-addressed by SHA-256 of the PNG bytes, so repeated
builds that produce identical figures reuse the same file. The cache lives at
``<spec_dir>/.folio-cache/charts/`` by default; override with the
``FOLIO_CHART_CACHE_DIR`` environment variable or the ``cache_dir=`` argument.
"""

from __future__ import annotations

import os
from collections.abc import Callable
from hashlib import sha256
from io import BytesIO
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
    """Record the spec directory so cached PNGs land next to the spec.

    Called by the DSL loader before executing a spec module. Cache references
    embedded in the rendered Element are resolved relative to this base.
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


def _import_pyplot() -> Any:
    try:
        import matplotlib
    except ImportError as exc:
        raise RuntimeError(
            "chart() requires matplotlib. Install the optional extra with "
            "`pip install 'folio[charts]'` or add matplotlib directly."
        ) from exc
    matplotlib.use("Agg", force=False)
    import matplotlib.pyplot as plt

    return plt


def _figure_to_png_bytes(fig: Figure, *, dpi: int, transparent: bool) -> bytes:
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
    """Builds a folio Element from a matplotlib Figure.

    Obtain one via :func:`chart`. Drive it in whichever form fits:

    - ``@handle`` decorator (function takes an Axes)
    - ``with handle as ax:`` context manager
    - ``handle.from_figure(fig)`` for a pre-built Figure

    The underlying Figure is always closed when folio owns it. When you hand
    in a pre-built Figure via :meth:`from_figure`, folio leaves it alone so
    you can keep using it.
    """

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
        self._x_mm = x_mm
        self._y_mm = y_mm
        self._width_mm = width_mm
        self._height_mm = height_mm
        self._dpi = dpi
        self._transparent = transparent
        self._cache_dir = _resolve_cache_dir(cache_dir)
        self._figure_kwargs = figure_kwargs
        self._image_attrs = image_attrs
        self._fig: Figure | None = None
        self._element: Element | None = None

    @property
    def element(self) -> Element:
        if self._element is None:
            raise RuntimeError(
                f"chart('{self._element_id}') has no element yet — "
                "use it as a decorator, enter the with-block, or call from_figure()"
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
        plt = _import_pyplot()
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
        try:
            if exc_type is None and fig is not None:
                self._rasterize(fig)
        finally:
            if fig is not None:
                _import_pyplot().close(fig)
            self._fig = None

    def __call__(self, render: Callable[[Axes], None]) -> Element:
        if not callable(render):
            raise TypeError("chart() decorator target must be callable (render function)")
        with self as ax:
            render(ax)
        return self.element

    def from_figure(self, fig: Figure) -> Element:
        """Rasterize a pre-built matplotlib Figure without owning its lifecycle.

        Use this for libraries that hand back a Figure (seaborn, pandas,
        ``Figure``-returning helpers). The caller keeps the Figure and is
        responsible for closing it if that matters for memory.
        """
        if fig is None or not hasattr(fig, "savefig"):
            raise TypeError("chart().from_figure(fig) expects a matplotlib Figure")
        self._rasterize(fig)
        return self.element

    def _rasterize(self, fig: Figure) -> None:
        png_bytes = _figure_to_png_bytes(fig, dpi=self._dpi, transparent=self._transparent)
        digest = sha256(png_bytes).hexdigest()[:16]
        self._cache_dir.mkdir(parents=True, exist_ok=True)
        png_path = self._cache_dir / f"{self._element_id}-{digest}.png"
        if not png_path.exists():
            png_path.write_bytes(png_bytes)
        self._element = _builtins.image(
            self._element_id,
            self._reference_for(png_path),
            self._x_mm,
            self._y_mm,
            self._width_mm,
            self._height_mm,
            **self._image_attrs,
        )

    @staticmethod
    def _reference_for(png_path: Path) -> str:
        anchor = _spec_base_dir if _spec_base_dir is not None else Path.cwd()
        try:
            return str(png_path.relative_to(anchor))
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
    """Create a :class:`ChartHandle` for a matplotlib-backed Element.

    :param element_id: Stable DSL id for reconcile.
    :param x_mm, y_mm: Top-left placement on the page (mm).
    :param width_mm, height_mm: Rendered size on the page (mm). The Figure
        is created with the same aspect so text scales predictably.
    :param dpi: Rasterization DPI. 300 is print-ready; drop to 150 for drafts.
    :param transparent: If True, the Figure background is left transparent
        so folio page tokens show through.
    :param cache_dir: Override the default ``<spec>/.folio-cache/charts`` path.
    :param figure_kwargs: Extra kwargs forwarded to ``plt.figure(...)``.
    :param image_attrs: Extra attributes forwarded to ``image(...)`` (e.g.
        ``clip=``, ``opacity=``).
    """
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
