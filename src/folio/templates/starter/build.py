from __future__ import annotations

from pages import build_cover, build_features, build_metrics

from folio.dsl import render


def build():
    return render(build_cover(), build_features(), build_metrics())


__all__ = ["build"]
