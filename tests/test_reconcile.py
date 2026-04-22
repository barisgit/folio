from __future__ import annotations

from pathlib import Path

from folio.reconcile.diff import diff_svgs
from folio.reconcile.parse import parse_svg

BASE_SVG = """<?xml version='1.0' encoding='UTF-8'?>
<svg xmlns='http://www.w3.org/2000/svg'>
  <g id='cover' data-page-number='1' data-page-id='cover'>
    <text id='hero_line_1' x='45.35' y='198.43' font-size='38' fill='#ffffff'>Every bus.</text>
  </g>
</svg>
"""

EDITED_SVG = """<?xml version='1.0' encoding='UTF-8'?>
<svg xmlns='http://www.w3.org/2000/svg'>
  <g id='cover' data-page-number='1' data-page-id='cover'>
    <text id='hero_line_1' x='50.35' y='198.43' font-size='44' fill='#ffffff'>Every CAN bus.</text>
  </g>
</svg>
"""

STRUCTURED_SVG = """<?xml version='1.0' encoding='UTF-8'?>
<svg xmlns='http://www.w3.org/2000/svg'>
  <g id='cover' data-page-number='1' data-page-id='cover'>
    <text id='hero_line_3' x='45.35' y='198.43'>
      One <tspan id='hero_line_3_emphasis' fill='#c8a24a'>black box</tspan>.
    </text>
    <text id='feature_body' x='45.35' y='226.77'>
      <tspan id='feature_body_line_1' x='45.35' y='226.77'>Line 1</tspan>
      <tspan id='feature_body_line_2' x='45.35' y='240.95'>
        Line <tspan id='feature_body_line_2_emphasis'>2</tspan>
      </tspan>
    </text>
  </g>
</svg>
"""

EDITED_STRUCTURED_SVG = """<?xml version='1.0' encoding='UTF-8'?>
<svg xmlns='http://www.w3.org/2000/svg'>
  <g id='cover' data-page-number='1' data-page-id='cover'>
    <text id='hero_line_3' x='45.35' y='198.43'>
      One <tspan id='hero_line_3_emphasis' fill='#c8a24a'>white box</tspan>.
    </text>
    <text id='feature_body' x='45.35' y='226.77'>
      <tspan id='feature_body_line_1' x='45.35' y='226.77'>Line 1</tspan>
      <tspan id='feature_body_line_2' x='45.35' y='240.95'>
        Line <tspan id='feature_body_line_2_emphasis'>2</tspan>
      </tspan>
    </text>
  </g>
</svg>
"""


def test_diff_reports_text_and_position_changes(tmp_path: Path) -> None:
    base_path = tmp_path / "cover.svg"
    edited_path = tmp_path / "cover-edited.svg"
    base_path.write_text(BASE_SVG, encoding="utf-8")
    edited_path.write_text(EDITED_SVG, encoding="utf-8")

    result = diff_svgs(parse_svg(base_path), parse_svg(edited_path))

    assert result.page_number == 1
    assert len(result.changes) == 1
    attrs = result.changes[0]["attrs"]
    assert attrs["text"]["from"] == "Every bus."
    assert attrs["text"]["to"] == "Every CAN bus."
    assert attrs["x_mm"]["to"] == 17.76
    assert attrs["font_size_pt"]["to"] == 44.0


def test_parse_svg_preserves_inline_and_multiline_tspan_text(tmp_path: Path) -> None:
    svg_path = tmp_path / "structured.svg"
    svg_path.write_text(STRUCTURED_SVG, encoding="utf-8")

    parsed = parse_svg(svg_path)

    assert parsed.elements["hero_line_3"].text == "One black box."
    assert parsed.elements["hero_line_3_emphasis"].text == "black box"
    assert parsed.elements["feature_body"].text == "Line 1\nLine 2"
    assert parsed.elements["feature_body_line_2"].text == "Line 2"
    assert parsed.elements["feature_body_line_2_emphasis"].text == "2"


def test_diff_reports_text_changes_for_stable_tspan_ids(tmp_path: Path) -> None:
    base_path = tmp_path / "structured-base.svg"
    edited_path = tmp_path / "structured-edited.svg"
    base_path.write_text(STRUCTURED_SVG, encoding="utf-8")
    edited_path.write_text(EDITED_STRUCTURED_SVG, encoding="utf-8")

    result = diff_svgs(parse_svg(base_path), parse_svg(edited_path))
    changes = {change["id"]: change for change in result.changes}

    assert changes["hero_line_3_emphasis"]["attrs"]["text"] == {
        "from": "black box",
        "to": "white box",
    }
