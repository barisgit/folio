from __future__ import annotations

from folio.dsl import collection, document, drop_shadow, grain

from pages import build_cover, build_features, build_metrics


def build():
    shared_defs = (
        drop_shadow("hero_shadow", blur=22, dx=0, dy=16, alpha=0.6),
        drop_shadow("card_shadow", blur=5, dx=0, dy=3, alpha=0.14),
        drop_shadow("tile_shadow", blur=5, dx=0, dy=3, alpha=0.12),
        grain("paper_grain", base_frequency=1.1, num_octaves=2, alpha=0.05, seed=3),
    )
    return collection(
        document(
            "starter",
            pages=[build_cover(), build_features(), build_metrics()],
            filename="folio",
            title="Folio starter",
            defs=shared_defs,
        ),
    )


__all__ = ["build"]
