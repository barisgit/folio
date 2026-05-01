"""Byte-parity regression test: the Pydantic-backed playground state must
serialize to the exact same JSON as the legacy hand-rolled serializer.

The fixture ``legacy_state.json`` was captured with the previous dataclass
+ hand-rolled ``serialize_playground_state`` implementation, then frozen so
future refactors cannot silently drift the wire format.
"""

from __future__ import annotations

import json
from pathlib import Path
from textwrap import dedent

from folio.services.playground import load_playground_state
from folio.services.playground_server import serialize_playground_state

_SPEC = dedent(
    """
    from folio.dsl import TextStyle, collection, document, page, rect, text, tweaks

    theme = tweaks.group(
        "theme",
        primary=tweaks.color(default="#d9a64b"),
        hero_size_pt=tweaks.size_pt(default=58, min=32, max=76),
        panel_width=tweaks.size_mm(default=40),
        rebuilt=tweaks.color(default="#112233", mode="rebuild"),
        style=tweaks.choice(default="bold", options=("bold", "light", "calm")),
    )

    HERO = TextStyle(font_size_pt=theme.hero_size_pt, fill=theme.primary)


    def build():
        return collection(
            document(
                "demo",
                pages=[
                    page(
                        page_id="one",
                        filename="one.svg",
                        page_number=1,
                        elements=[
                            rect("panel", 0, 0, theme.panel_width, 20, fill=theme.rebuilt),
                            text("hero", 10, 20, "Hi", style=HERO),
                        ],
                    )
                ],
            )
        )
    """
).strip() + "\n"


_VALUES = '[theme]\nprimary = "#445566"\nhero_size_pt = 64\nstyle = "calm"\n'


_FIXTURE = Path(__file__).parent / "fixtures" / "playground" / "legacy_state.json"


def test_serialize_playground_state_matches_legacy_byte_for_byte(tmp_path: Path) -> None:
    spec_path = tmp_path / "build.py"
    spec_path.write_text(_SPEC, encoding="utf-8")
    (tmp_path / "theme.toml").write_text(_VALUES, encoding="utf-8")

    state = load_playground_state(spec_path)
    payload = serialize_playground_state(state)
    # Path fields are absolute and tmp-dependent; the fixture stubs them so
    # the rest of the payload is what the test actually pins.
    payload["specPath"] = "<SPEC>"
    payload["valuesPath"] = "<VALUES>"
    actual = json.dumps(payload, sort_keys=True, indent=2) + "\n"

    expected = _FIXTURE.read_text(encoding="utf-8")
    assert actual == expected, (
        "Wire-format drift detected. If the change is intentional, regenerate "
        f"{_FIXTURE.relative_to(Path(__file__).parent.parent)} and update "
        "consumers (browser playground UI) accordingly."
    )


def test_diagnostic_null_key_is_emitted_explicitly(tmp_path: Path) -> None:
    """The legacy wire format always emitted ``"key": null`` for diagnostics
    without a key. Pydantic would drop it under default exclude rules, so we
    rely on explicit nullable typing (no exclude_none) to keep the shape.
    """

    spec_path = tmp_path / "build.py"
    spec_path.write_text(_SPEC, encoding="utf-8")
    (tmp_path / "theme.toml").write_text(_VALUES, encoding="utf-8")
    state = load_playground_state(spec_path)
    payload = serialize_playground_state(state)

    # Tweaks with no min/max/label/options must still emit those keys with
    # null values; the legacy fixture confirms this for the `primary` tweak.
    primary = next(t for t in payload["tweaks"] if t["key"] == "theme.primary")
    assert primary["min"] is None
    assert primary["max"] is None
    assert primary["label"] is None
    assert primary["options"] is None
