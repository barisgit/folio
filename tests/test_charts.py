from __future__ import annotations

from pathlib import Path

import pytest

from folio.dsl import ChartHandle, Element, ElementKind, chart
from folio.dsl.model import Asset

matplotlib = pytest.importorskip("matplotlib")


def test_chart_decorator_returns_element(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.chdir(tmp_path)

    @chart(
        "revenue",
        x_mm=20.0,
        y_mm=40.0,
        width_mm=80.0,
        height_mm=40.0,
        dpi=96,
    )
    def revenue(ax) -> None:
        ax.plot([0, 1, 2, 3], [1, 3, 2, 5])

    assert isinstance(revenue, Element)
    assert revenue.kind is ElementKind.IMAGE
    assert revenue.element_id == "revenue"
    assert revenue.x_mm == pytest.approx(20.0)
    assert revenue.y_mm == pytest.approx(40.0)
    assert isinstance(revenue.content, Asset)
    assert revenue.content.width_mm == pytest.approx(80.0)
    assert revenue.content.height_mm == pytest.approx(40.0)

    reference = Path(revenue.content.reference)
    resolved = (tmp_path / reference) if not reference.is_absolute() else reference
    assert resolved.exists()
    assert resolved.suffix == ".png"
    assert resolved.stat().st_size > 0


def test_chart_context_manager_exposes_element(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.chdir(tmp_path)

    handle = chart(
        "trends",
        x_mm=10.0,
        y_mm=20.0,
        width_mm=50.0,
        height_mm=30.0,
        dpi=72,
    )
    assert isinstance(handle, ChartHandle)

    with pytest.raises(RuntimeError, match="no element yet"):
        _ = handle.element

    with handle as ax:
        assert handle.figure is not None
        ax.plot([0, 1], [0, 1])

    assert isinstance(handle.element, Element)
    assert handle.element.kind is ElementKind.IMAGE


def test_chart_cache_hit_reuses_png(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.chdir(tmp_path)

    def plot(ax) -> None:
        ax.plot([0, 1, 2], [2, 1, 3])
        ax.set_xlim(0, 2)
        ax.set_ylim(0, 3)

    first = chart(
        "cached", x_mm=0.0, y_mm=0.0, width_mm=40.0, height_mm=20.0, dpi=72
    )(plot)
    second = chart(
        "cached", x_mm=0.0, y_mm=0.0, width_mm=40.0, height_mm=20.0, dpi=72
    )(plot)

    assert first.content.reference == second.content.reference
    cache_file = (tmp_path / first.content.reference).resolve()
    assert cache_file.exists()


def test_chart_requires_positive_dimensions(tmp_path: Path) -> None:
    with pytest.raises(TypeError, match="width_mm and height_mm"):
        chart("bad", x_mm=0.0, y_mm=0.0, width_mm=0.0, height_mm=10.0)


def test_chart_requires_element_id() -> None:
    with pytest.raises(TypeError, match="non-empty element_id"):
        chart("", x_mm=0.0, y_mm=0.0, width_mm=10.0, height_mm=10.0)


def test_chart_from_figure_rasterizes_pre_built_figure(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.chdir(tmp_path)

    import matplotlib.pyplot as plt

    fig = plt.figure(figsize=(2.0, 1.0), dpi=72)
    ax = fig.add_subplot(111)
    ax.plot([0, 1, 2], [0, 2, 1])

    element = chart(
        "prebuilt", x_mm=0.0, y_mm=0.0, width_mm=40.0, height_mm=20.0, dpi=72
    ).from_figure(fig)

    assert isinstance(element, Element)
    assert element.kind is ElementKind.IMAGE

    reference = Path(element.content.reference)
    resolved = reference if reference.is_absolute() else tmp_path / reference
    assert resolved.exists()

    assert fig.axes, "from_figure() must not close the caller's Figure"
    plt.close(fig)


def test_chart_from_figure_rejects_non_figure() -> None:
    with pytest.raises(TypeError, match="matplotlib Figure"):
        chart("bad", x_mm=0.0, y_mm=0.0, width_mm=10.0, height_mm=10.0).from_figure(None)  # type: ignore[arg-type]


def test_chart_environment_cache_override(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    cache_dir = tmp_path / "custom-cache"
    monkeypatch.setenv("FOLIO_CHART_CACHE_DIR", str(cache_dir))

    handle = chart(
        "env_cached", x_mm=0.0, y_mm=0.0, width_mm=30.0, height_mm=20.0, dpi=72
    )

    @handle
    def _render(ax) -> None:
        ax.plot([0, 1], [0, 1])

    reference = Path(_render.content.reference)
    resolved = reference if reference.is_absolute() else Path.cwd() / reference
    assert resolved.resolve().is_relative_to(cache_dir.resolve())
