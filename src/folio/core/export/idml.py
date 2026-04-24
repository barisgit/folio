# ruff: noqa: E501
from __future__ import annotations

import html
import re
import zipfile
from dataclasses import dataclass
from pathlib import Path
from typing import Any, cast

from folio.core.dsl.styles import merge_text_style_attrs
from folio.core.model import Document, Element, ElementKind, Markup, Page, TextSpan
from folio.core.render.primitives import m

_IDML_MIMETYPE = "application/vnd.adobe.indesign-idml-package"
_IDML_NAMESPACE = "http://ns.adobe.com/AdobeInDesign/idml/1.0/packaging"
_DOM_VERSION = "18.5"
_DEFAULT_PACKAGE_NAME = "folio.idml"
_LAYER_ID = "u1"
_MASTER_SPREAD_ID = "u2"
_NONE_COLOR = "Color/None"
_PAPER_COLOR = "Color/Paper"
_BLACK_COLOR = "Color/Black"


@dataclass(frozen=True)
class _NativePage:
    page: Page
    spread_id: str
    page_id: str
    width_pt: float
    height_pt: float
    items_xml: str


@dataclass(frozen=True)
class _Story:
    story_id: str
    content: str
    point_size: float
    fill_color: str
    font_style: str


class _IdGenerator:
    def __init__(self, start: int = 100) -> None:
        self._next = start

    def next(self) -> str:
        value = f"u{self._next}"
        self._next += 1
        return value


class _ColorRegistry:
    def __init__(self) -> None:
        self._colors: dict[str, tuple[int, int, int]] = {}

    def ref(self, value: object, *, default: str = _NONE_COLOR) -> str:
        if value is None:
            return default
        text = str(value).strip()
        if not text or text.lower() in {"none", "transparent"}:
            return _NONE_COLOR
        if text.lower() in {"black", "$id/black"}:
            return _BLACK_COLOR
        if text.lower() in {"white", "paper", "$id/paper"}:
            return _PAPER_COLOR
        rgb = _parse_hex_color(text)
        if rgb is None:
            return default
        name = f"Folio_{rgb[0]:02X}{rgb[1]:02X}{rgb[2]:02X}"
        self._colors[name] = rgb
        return f"Color/{name}"

    def xml(self) -> str:
        entries = []
        for name, (red, green, blue) in sorted(self._colors.items()):
            entries.append(
                f'  <Color Self="Color/{name}" Name="{name}" Model="Process" Space="RGB" ColorValue="{red} {green} {blue}" AlternateSpace="NoAlternateColor"/>'
            )
        return "\n".join(entries)


def write_idml(
    document: Document,
    out_dir: Path,
    *,
    package_name: str = _DEFAULT_PACKAGE_NAME,
) -> Path:
    """Write a native editable IDML package for a Folio document.

    The MVP maps common Folio DSL primitives to native IDML page items instead
    of placing whole-page snapshots. Rectangles, text frames, lines, ovals,
    polygons, polylines, and groups are editable in layout applications that
    import IDML. Unsupported SVG-only features such as defs, filters, gradients,
    and arbitrary path commands are intentionally skipped for now instead of
    rasterizing the entire page.
    """

    out_dir.mkdir(parents=True, exist_ok=True)
    target = out_dir / _safe_package_name(package_name)
    ids = _IdGenerator()
    colors = _ColorRegistry()
    stories: list[_Story] = []
    pages = _native_pages(document, ids=ids, colors=colors, stories=stories)

    with zipfile.ZipFile(target, "w") as package:
        _write_mimetype(package)
        _writestr(package, "META-INF/container.xml", _container_xml())
        _writestr(package, "designmap.xml", _designmap_xml(pages, stories))
        _writestr(package, "Resources/Preferences.xml", _preferences_xml(pages))
        _writestr(package, "Resources/Styles.xml", _styles_xml())
        _writestr(package, "Resources/Graphic.xml", _graphic_xml(colors))
        _writestr(package, "Resources/Fonts.xml", _fonts_xml())
        _writestr(package, "MasterSpreads/MasterSpread_ub4.xml", _master_spread_xml())
        _writestr(package, "XML/BackingStory.xml", _backing_story_xml())
        _writestr(package, "XML/Tags.xml", _tags_xml())
        for page in pages:
            _writestr(package, f"Spreads/Spread_{page.spread_id}.xml", _spread_xml(page))
        for story in stories:
            _writestr(package, f"Stories/Story_{story.story_id}.xml", _story_xml(story))

    return target


def _write_mimetype(package: zipfile.ZipFile) -> None:
    info = zipfile.ZipInfo("mimetype")
    info.compress_type = zipfile.ZIP_STORED
    package.writestr(info, _IDML_MIMETYPE)


def _writestr(package: zipfile.ZipFile, name: str, content: str) -> None:
    info = zipfile.ZipInfo(name)
    info.compress_type = zipfile.ZIP_DEFLATED
    package.writestr(info, content.encode("utf-8"))


def _native_pages(
    document: Document,
    *,
    ids: _IdGenerator,
    colors: _ColorRegistry,
    stories: list[_Story],
) -> list[_NativePage]:
    pages: list[_NativePage] = []
    for page in sorted(document.pages, key=lambda candidate: candidate.page_number):
        items = "".join(
            _element_xml(element, page=page, ids=ids, colors=colors, stories=stories)
            for element in page.elements
        )
        pages.append(
            _NativePage(
                page=page,
                spread_id=ids.next(),
                page_id=ids.next(),
                width_pt=m(page.width_mm),
                height_pt=m(page.height_mm),
                items_xml=items,
            )
        )
    return pages


def _element_xml(
    element: Element,
    *,
    page: Page,
    ids: _IdGenerator,
    colors: _ColorRegistry,
    stories: list[_Story],
) -> str:
    if element.kind is ElementKind.RECT:
        return _rect_xml(element, ids=ids, colors=colors)
    if element.kind is ElementKind.TEXT:
        return _text_frame_xml(element, page=page, ids=ids, colors=colors, stories=stories)
    if element.kind is ElementKind.LINE:
        return _line_xml(element, ids=ids, colors=colors)
    if element.kind is ElementKind.CIRCLE:
        radius = float(element.attrs.get("radius_mm", 0))
        return _oval_xml(
            element,
            left_mm=element.x_mm - radius,
            top_mm=element.y_mm - radius,
            width_mm=radius * 2,
            height_mm=radius * 2,
            ids=ids,
            colors=colors,
        )
    if element.kind is ElementKind.ELLIPSE:
        rx = float(element.attrs.get("rx_mm", 0))
        ry = float(element.attrs.get("ry_mm", 0))
        return _oval_xml(
            element,
            left_mm=element.x_mm - rx,
            top_mm=element.y_mm - ry,
            width_mm=rx * 2,
            height_mm=ry * 2,
            ids=ids,
            colors=colors,
        )
    if element.kind in {ElementKind.POLYGON, ElementKind.POLYLINE}:
        return _point_shape_xml(
            element,
            closed=element.kind is ElementKind.POLYGON,
            ids=ids,
            colors=colors,
        )
    if element.kind is ElementKind.GROUP:
        return "".join(
            _element_xml(child, page=page, ids=ids, colors=colors, stories=stories)
            for child in element.children
        )
    return f"<!-- Folio IDML MVP skipped unsupported editable element {_xml(element.element_id)} ({element.kind.name}) -->\n"


def _rect_xml(element: Element, *, ids: _IdGenerator, colors: _ColorRegistry) -> str:
    attrs = dict(element.attrs)
    width_mm = float(attrs.pop("width_mm"))
    height_mm = float(attrs.pop("height_mm"))
    return _path_page_item_xml(
        tag="Rectangle",
        self_id=ids.next(),
        name=element.element_id,
        bounds=_bounds(element.x_mm, element.y_mm, width_mm, height_mm),
        points=_rectangle_points(element.x_mm, element.y_mm, width_mm, height_mm),
        closed=True,
        fill_color=colors.ref(_pop_attr(attrs, "fill"), default=_NONE_COLOR),
        stroke_color=colors.ref(_pop_attr(attrs, "stroke"), default=_NONE_COLOR),
        stroke_weight=_stroke_weight(attrs),
    )


def _oval_xml(
    element: Element,
    *,
    left_mm: float,
    top_mm: float,
    width_mm: float,
    height_mm: float,
    ids: _IdGenerator,
    colors: _ColorRegistry,
) -> str:
    attrs = dict(element.attrs)
    return _basic_page_item_xml(
        tag="Oval",
        self_id=ids.next(),
        name=element.element_id,
        bounds=_bounds(left_mm, top_mm, width_mm, height_mm),
        content_type="Unassigned",
        fill_color=colors.ref(_pop_attr(attrs, "fill"), default=_NONE_COLOR),
        stroke_color=colors.ref(_pop_attr(attrs, "stroke"), default=_NONE_COLOR),
        stroke_weight=_stroke_weight(attrs),
    )


def _line_xml(element: Element, *, ids: _IdGenerator, colors: _ColorRegistry) -> str:
    if not isinstance(element.content, tuple) or len(element.content) != 2:
        return f"<!-- Folio IDML MVP skipped invalid line {_xml(element.element_id)} -->\n"
    attrs = dict(element.attrs)
    x1 = float(element.x_mm)
    y1 = float(element.y_mm)
    x2 = float(element.content[0])
    y2 = float(element.content[1])
    left = min(x1, x2)
    top = min(y1, y2)
    return _path_page_item_xml(
        tag="GraphicLine",
        self_id=ids.next(),
        name=element.element_id,
        bounds=(m(top), m(left), m(max(y1, y2)), m(max(x1, x2))),
        points=((m(x1), m(y1)), (m(x2), m(y2))),
        closed=False,
        fill_color=_NONE_COLOR,
        stroke_color=colors.ref(_pop_attr(attrs, "stroke"), default=_BLACK_COLOR),
        stroke_weight=_stroke_weight(attrs, default=1.0),
    )


def _point_shape_xml(
    element: Element,
    *,
    closed: bool,
    ids: _IdGenerator,
    colors: _ColorRegistry,
) -> str:
    if not isinstance(element.content, tuple) or len(element.content) < 2:
        return f"<!-- Folio IDML MVP skipped invalid point shape {_xml(element.element_id)} -->\n"
    attrs = dict(element.attrs)
    points_mm = tuple((float(x), float(y)) for x, y in element.content)
    xs = [point[0] for point in points_mm]
    ys = [point[1] for point in points_mm]
    points_pt = tuple((m(x), m(y)) for x, y in points_mm)
    return _path_page_item_xml(
        tag="Polygon" if closed else "GraphicLine",
        self_id=ids.next(),
        name=element.element_id,
        bounds=(m(min(ys)), m(min(xs)), m(max(ys)), m(max(xs))),
        points=points_pt,
        closed=closed,
        fill_color=colors.ref(_pop_attr(attrs, "fill"), default=_NONE_COLOR),
        stroke_color=colors.ref(_pop_attr(attrs, "stroke"), default=_NONE_COLOR),
        stroke_weight=_stroke_weight(attrs),
    )


def _text_frame_xml(
    element: Element,
    *,
    page: Page,
    ids: _IdGenerator,
    colors: _ColorRegistry,
    stories: list[_Story],
) -> str:
    attrs = merge_text_style_attrs(
        dict(element.attrs),
        source=f"Text element {element.element_id}",
        for_span=False,
    )
    point_size = float(attrs.pop("size_pt", 12))
    weight = int(attrs.pop("weight", 400))
    fill_color = colors.ref(attrs.pop("fill", "#000000"), default=_BLACK_COLOR)
    font_style = str(attrs.pop("font_style", ""))
    italic = bool(attrs.pop("italic", False))
    if not font_style:
        if italic and weight >= 700:
            font_style = "Bold Italic"
        elif italic:
            font_style = "Italic"
        elif weight >= 700:
            font_style = "Bold"
        else:
            font_style = "Regular"

    lines = _text_lines(element.content)
    story = _Story(
        story_id=ids.next(),
        content="\n".join(lines),
        point_size=point_size,
        fill_color=fill_color,
        font_style=font_style,
    )
    stories.append(story)

    left = m(element.x_mm)
    top = max(0.0, m(element.y_mm) - point_size)
    width_mm = float(
        _pop_attr(attrs, "width_mm", "width", default=max(10.0, page.width_mm - element.x_mm))
    )
    line_count = max(1, len(lines))
    height = point_size * max(1.25, line_count * 1.35)
    bounds = (top, left, top + height, left + m(width_mm))
    return f"""      <TextFrame Self="{ids.next()}" Name="{_xml(element.element_id)}" ParentStory="{_xml(story.story_id)}" ContentType="TextType" AppliedObjectStyle="ObjectStyle/$ID/[None]" ItemLayer="{_LAYER_ID}" Visible="true" Locked="false" ItemTransform="1 0 0 1 0 0" GeometricBounds="{_bounds_text(bounds)}" FillColor="{_NONE_COLOR}" StrokeColor="{_NONE_COLOR}" StrokeWeight="0">
        <Properties>
{_path_geometry(_rectangle_points_pt(bounds), closed=True, indent="          ")}
        </Properties>
        <TextFramePreference TextColumnCount="1" VerticalJustification="TopAlign" FirstBaselineOffset="LeadingOffset"/>
      </TextFrame>
"""


def _basic_page_item_xml(
    *,
    tag: str,
    self_id: str,
    name: str,
    bounds: tuple[float, float, float, float],
    content_type: str,
    fill_color: str,
    stroke_color: str,
    stroke_weight: float,
) -> str:
    return f'      <{tag} Self="{_xml(self_id)}" Name="{_xml(name)}" ParentStory="n" ContentType="{content_type}" AppliedObjectStyle="ObjectStyle/$ID/[None]" ItemLayer="{_LAYER_ID}" Visible="true" Locked="false" ItemTransform="1 0 0 1 0 0" GeometricBounds="{_bounds_text(bounds)}" FillColor="{_xml(fill_color)}" StrokeColor="{_xml(stroke_color)}" StrokeWeight="{_fmt(stroke_weight)}"/>\n'


def _path_page_item_xml(
    *,
    tag: str,
    self_id: str,
    name: str,
    bounds: tuple[float, float, float, float],
    points: tuple[tuple[float, float], ...],
    closed: bool,
    fill_color: str,
    stroke_color: str,
    stroke_weight: float,
) -> str:
    return f"""      <{tag} Self="{_xml(self_id)}" Name="{_xml(name)}" ParentStory="n" ContentType="Unassigned" AppliedObjectStyle="ObjectStyle/$ID/[None]" ItemLayer="{_LAYER_ID}" Visible="true" Locked="false" ItemTransform="1 0 0 1 0 0" GeometricBounds="{_bounds_text(bounds)}" FillColor="{_xml(fill_color)}" StrokeColor="{_xml(stroke_color)}" StrokeWeight="{_fmt(stroke_weight)}">
        <Properties>
{_path_geometry(points, closed=closed, indent="          ")}
        </Properties>
      </{tag}>
"""


def _path_geometry(points: tuple[tuple[float, float], ...], *, closed: bool, indent: str) -> str:
    path_open = "false" if closed else "true"
    point_xml = "\n".join(
        f'{indent}      <PathPointType Anchor="{_fmt(x)} {_fmt(y)}" LeftDirection="{_fmt(x)} {_fmt(y)}" RightDirection="{_fmt(x)} {_fmt(y)}"/>'
        for x, y in points
    )
    return f"""{indent}<PathGeometry>
{indent}  <GeometryPathType PathOpen="{path_open}">
{indent}    <PathPointArray>
{point_xml}
{indent}    </PathPointArray>
{indent}  </GeometryPathType>
{indent}</PathGeometry>"""


def _rectangle_points(
    left_mm: float, top_mm: float, width_mm: float, height_mm: float
) -> tuple[tuple[float, float], ...]:
    left = m(left_mm)
    top = m(top_mm)
    right = m(left_mm + width_mm)
    bottom = m(top_mm + height_mm)
    return ((left, top), (right, top), (right, bottom), (left, bottom))


def _rectangle_points_pt(
    bounds: tuple[float, float, float, float],
) -> tuple[tuple[float, float], ...]:
    top, left, bottom, right = bounds
    return ((left, top), (right, top), (right, bottom), (left, bottom))


def _bounds(
    left_mm: float, top_mm: float, width_mm: float, height_mm: float
) -> tuple[float, float, float, float]:
    return (m(top_mm), m(left_mm), m(top_mm + height_mm), m(left_mm + width_mm))


def _bounds_text(bounds: tuple[float, float, float, float]) -> str:
    top, left, bottom, right = bounds
    return f"{_fmt(top)} {_fmt(left)} {_fmt(bottom)} {_fmt(right)}"


ContentPart = str | Markup | TextSpan


def _text_lines(content: object) -> list[str]:
    if isinstance(content, str):
        return [content]
    if isinstance(content, Markup):
        return [_strip_markup(content.value)]
    if isinstance(content, TextSpan):
        return _text_lines(content.content)
    if isinstance(content, tuple):
        parts = [_text_from_part(part) for part in cast(tuple[ContentPart, ...], content)]
        return [part for part in parts if part]
    if content is None:
        return [""]
    return [str(content)]


def _text_from_part(part: ContentPart) -> str:
    if isinstance(part, str):
        return part
    if isinstance(part, Markup):
        return _strip_markup(part.value)
    lines = _text_lines(part.content)
    return "".join(lines) if len(lines) == 1 else "\n".join(lines)


def _strip_markup(value: str) -> str:
    return re.sub(r"<[^>]+>", "", value)


def _pop_attr(attrs: dict[str, Any], *names: str, default: Any = None) -> Any:
    for name in names:
        if name in attrs:
            return attrs.pop(name)
        dashed = name.replace("_", "-")
        if dashed in attrs:
            return attrs.pop(dashed)
    return default


def _stroke_weight(attrs: dict[str, Any], *, default: float = 0.0) -> float:
    value = _pop_attr(attrs, "stroke_width", "stroke-width", default=None)
    if value is None:
        return default
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def _parse_hex_color(value: str) -> tuple[int, int, int] | None:
    match = re.fullmatch(r"#([0-9a-fA-F]{3}|[0-9a-fA-F]{4}|[0-9a-fA-F]{6}|[0-9a-fA-F]{8})", value)
    if match is None:
        return None
    raw = match.group(1)
    if len(raw) in {3, 4}:
        raw = "".join(channel * 2 for channel in raw[:3])
    else:
        raw = raw[:6]
    return (int(raw[0:2], 16), int(raw[2:4], 16), int(raw[4:6], 16))


def _safe_package_name(package_name: str) -> str:
    name = Path(package_name).name or _DEFAULT_PACKAGE_NAME
    if name in {".", ".."}:
        name = _DEFAULT_PACKAGE_NAME
    if not name.lower().endswith(".idml"):
        name = f"{name}.idml"
    return name


def _xml(value: object) -> str:
    return html.escape(str(value), quote=True)


def _fmt(value: float) -> str:
    return f"{value:.4f}".rstrip("0").rstrip(".")


def _container_xml() -> str:
    return """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<container version="1.0" xmlns="urn:oasis:names:tc:opendocument:xmlns:container">
  <rootfiles>
    <rootfile full-path="designmap.xml" media-type="application/vnd.adobe.indesign-idml-package"/>
  </rootfiles>
</container>
"""


def _designmap_xml(pages: list[_NativePage], stories: list[_Story]) -> str:
    spread_refs = "\n".join(
        f'  <idPkg:Spread src="Spreads/Spread_{_xml(page.spread_id)}.xml"/>' for page in pages
    )
    story_refs = "\n".join(
        f'  <idPkg:Story src="Stories/Story_{_xml(story.story_id)}.xml"/>' for story in stories
    )
    return f"""<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Document DOMVersion="{_DOM_VERSION}" Self="d" xmlns:idPkg="{_IDML_NAMESPACE}">
  <Properties>
    <Label>
      <KeyValuePair Key="FolioExporter" Value="native-editable-mvp"/>
    </Label>
  </Properties>
  <idPkg:Preferences src="Resources/Preferences.xml"/>
  <idPkg:Graphic src="Resources/Graphic.xml"/>
  <idPkg:Fonts src="Resources/Fonts.xml"/>
  <idPkg:Styles src="Resources/Styles.xml"/>
  <Layer Self="{_LAYER_ID}" Name="Folio pages" Visible="true" Locked="false" IgnoreWrap="false" ShowGuides="true" LockGuides="false" UI="true" Expendable="true" Printable="true"/>
  <idPkg:MasterSpread src="MasterSpreads/MasterSpread_ub4.xml"/>
{spread_refs}
{story_refs}
</Document>
"""


def _preferences_xml(pages: list[_NativePage]) -> str:
    first = pages[0] if pages else None
    width = _fmt(first.width_pt if first else m(210.0))
    height = _fmt(first.height_pt if first else m(297.0))
    return f"""<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<idPkg:Preferences xmlns:idPkg="{_IDML_NAMESPACE}" DOMVersion="{_DOM_VERSION}">
  <DocumentPreference Self="DocumentPreference/$ID/DocumentPreference" PageWidth="{width}" PageHeight="{height}" FacingPages="false" PagesPerDocument="{len(pages)}" AllowPageShuffle="true" PreserveLayoutWhenShuffling="true"/>
  <PrintPreference Self="PrintPreference/$ID/PrintPreference" PageRange="AllPages"/>
</idPkg:Preferences>
"""


def _styles_xml() -> str:
    return f"""<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<idPkg:Styles xmlns:idPkg="{_IDML_NAMESPACE}" DOMVersion="{_DOM_VERSION}">
  <RootCharacterStyleGroup Self="u10">
    <CharacterStyle Self="CharacterStyle/$ID/[No character style]" Name="$ID/[No character style]" Imported="false" NextStyle="CharacterStyle/$ID/[No character style]" KeyboardShortcut="0 0"/>
  </RootCharacterStyleGroup>
  <RootParagraphStyleGroup Self="u11">
    <ParagraphStyle Self="ParagraphStyle/$ID/NormalParagraphStyle" Name="$ID/NormalParagraphStyle" Imported="false" NextStyle="ParagraphStyle/$ID/NormalParagraphStyle" KeyboardShortcut="0 0"/>
  </RootParagraphStyleGroup>
  <RootObjectStyleGroup Self="u12">
    <ObjectStyle Self="ObjectStyle/$ID/[None]" Name="$ID/[None]" Imported="false" KeyboardShortcut="0 0" EnableFill="true" EnableStroke="true" EnableTransparency="true"/>
  </RootObjectStyleGroup>
</idPkg:Styles>
"""


def _graphic_xml(colors: _ColorRegistry) -> str:
    custom = colors.xml()
    if custom:
        custom = f"\n{custom}"
    return f"""<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<idPkg:Graphic xmlns:idPkg="{_IDML_NAMESPACE}" DOMVersion="{_DOM_VERSION}">
  <Color Self="Color/Black" Name="Black" Model="Process" Space="CMYK" ColorValue="0 0 0 100" ColorOverride="Specialblack" AlternateSpace="NoAlternateColor"/>
  <Color Self="Color/Paper" Name="Paper" Model="Process" Space="CMYK" ColorValue="0 0 0 0" AlternateSpace="NoAlternateColor"/>
  <Color Self="Color/None" Name="None" Model="Process" Space="CMYK" ColorValue="0 0 0 0" AlternateSpace="NoAlternateColor"/>
  <StrokeStyle Self="StrokeStyle/$ID/Solid" Name="$ID/Solid" StrokeStyleType="Solid"/>{custom}
</idPkg:Graphic>
"""


def _fonts_xml() -> str:
    return f"""<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<idPkg:Fonts xmlns:idPkg="{_IDML_NAMESPACE}" DOMVersion="{_DOM_VERSION}">
  <CompositeFont Self="CompositeFont/$ID/[No composite font]" Name="$ID/[No composite font]"/>
</idPkg:Fonts>
"""


def _master_spread_xml() -> str:
    return f"""<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<idPkg:MasterSpread xmlns:idPkg="{_IDML_NAMESPACE}" DOMVersion="{_DOM_VERSION}">
  <MasterSpread Self="{_MASTER_SPREAD_ID}" NamePrefix="A" BaseName="Master" ShowMasterItems="true" PageCount="1" PrimaryTextFrame="n"/>
</idPkg:MasterSpread>
"""


def _backing_story_xml() -> str:
    return f"""<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<idPkg:BackingStory xmlns:idPkg="{_IDML_NAMESPACE}" DOMVersion="{_DOM_VERSION}">
  <XmlStory Self="ubacking"/>
</idPkg:BackingStory>
"""


def _tags_xml() -> str:
    return f"""<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<idPkg:Tags xmlns:idPkg="{_IDML_NAMESPACE}" DOMVersion="{_DOM_VERSION}">
  <XMLTag Self="XMLTag/Root" Name="Root" MarkupTagColor="UIColors/LIGHT_BLUE"/>
</idPkg:Tags>
"""


def _spread_xml(page: _NativePage) -> str:
    width = _fmt(page.width_pt)
    height = _fmt(page.height_pt)
    label = _xml(page.page.label or page.page.page_id)
    return f"""<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<idPkg:Spread xmlns:idPkg="{_IDML_NAMESPACE}" DOMVersion="{_DOM_VERSION}">
  <Spread Self="{_xml(page.spread_id)}" FlattenerOverride="Default" AllowPageShuffle="true" ItemTransform="1 0 0 1 0 0">
    <Page Self="{_xml(page.page_id)}" Name="{page.page.page_number}" AppliedMaster="n" MasterPageTransform="1 0 0 1 0 0" GeometricBounds="0 0 {height} {width}" ItemTransform="1 0 0 1 0 0" OverrideList="" TabOrder="">
      <Properties>
        <Descriptor type="string">{label}</Descriptor>
      </Properties>
    </Page>
{page.items_xml}  </Spread>
</idPkg:Spread>
"""


def _story_xml(story: _Story) -> str:
    paragraphs = "".join(
        f"""    <ParagraphStyleRange AppliedParagraphStyle="ParagraphStyle/$ID/NormalParagraphStyle">
      <CharacterStyleRange AppliedCharacterStyle="CharacterStyle/$ID/[No character style]" PointSize="{_fmt(story.point_size)}" FillColor="{_xml(story.fill_color)}" FontStyle="{_xml(story.font_style)}">
        <Content>{_xml(line)}</Content>
      </CharacterStyleRange>
    </ParagraphStyleRange>
"""
        for line in story.content.split("\n")
    )
    return f"""<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<idPkg:Story xmlns:idPkg="{_IDML_NAMESPACE}" DOMVersion="{_DOM_VERSION}">
  <Story Self="{_xml(story.story_id)}" UserText="true" IsEndnoteStory="false" AppliedTOCStyle="n" TrackChanges="false" StoryTitle="$ID/" AppliedNamedGrid="n">
    <StoryPreference OpticalMarginAlignment="false" OpticalMarginSize="12" FrameType="TextFrameType" StoryOrientation="Horizontal" StoryDirection="LeftToRightDirection"/>
    <InCopyExportOption IncludeGraphicProxies="true" IncludeAllResources="false"/>
{paragraphs}  </Story>
</idPkg:Story>
"""
