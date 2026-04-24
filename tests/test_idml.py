from __future__ import annotations

import xml.etree.ElementTree as ET
import zipfile
from pathlib import Path
from textwrap import dedent

from typer.testing import CliRunner

from folio.cli import app
from folio.dsl.loader import load_dsl_module
from folio.dsl.renderer import document_from_module
from folio.export.idml import write_idml

runner = CliRunner()


def _write_spec(path: Path) -> None:
    path.write_text(
        dedent(
            """
            from folio.dsl import idml, page, line, rect, render, text

            def build():
                return render(
                    page(
                        rect("bg", 0, 0, 100, 50, fill="#ffffff"),
                        text("headline", 10, 20, "Hello", size_pt=12, fill="#112233"),
                        line("rule", 10, 25, 90, 25, stroke="#112233", stroke_width=0.5),
                        page_id="cover",
                        filename="cover.svg",
                        page_number=1,
                        width_mm=100,
                        height_mm=50,
                    ),
                    page(
                        rect("inside_bg", 0, 0, 100, 50, fill="#eeeeee"),
                        text("body", 10, 20, "World", size_pt=12),
                        page_id="inside",
                        filename="inside.svg",
                        page_number=2,
                        width_mm=100,
                        height_mm=50,
                    ),
                    export_presets=[idml()],
                    default_exports=["idml"],
                )
            """
        ).strip()
        + "\n",
        encoding="utf-8",
    )


def _document(path: Path):
    return document_from_module(load_dsl_module(path))


def test_write_idml_packages_native_editable_objects(tmp_path: Path) -> None:
    spec_path = tmp_path / "build.py"
    _write_spec(spec_path)

    target = write_idml(_document(spec_path), tmp_path / "out")

    assert target == tmp_path / "out" / "folio.idml"
    with zipfile.ZipFile(target) as package:
        names = package.namelist()
        assert names[0] == "mimetype"
        assert package.getinfo("mimetype").compress_type == zipfile.ZIP_STORED
        assert package.read("mimetype").decode() == "application/vnd.adobe.indesign-idml-package"
        assert "designmap.xml" in names
        assert "Resources/Preferences.xml" in names
        assert "Resources/Styles.xml" in names
        assert "Resources/Graphic.xml" in names
        assert "Resources/Fonts.xml" in names
        assert "MasterSpreads/MasterSpread_ub4.xml" in names
        assert "XML/BackingStory.xml" in names
        assert "XML/Tags.xml" in names
        spread_names = [name for name in names if name.startswith("Spreads/Spread_")]
        story_names = [name for name in names if name.startswith("Stories/Story_")]
        assert len(spread_names) == 2
        assert len(story_names) == 2
        assert not any(name.startswith("Links/") for name in names)


def test_write_idml_xml_entries_are_well_formed(tmp_path: Path) -> None:
    spec_path = tmp_path / "build.py"
    _write_spec(spec_path)

    target = write_idml(_document(spec_path), tmp_path / "out")

    with zipfile.ZipFile(target) as package:
        for name in package.namelist():
            if name.endswith(".xml"):
                ET.fromstring(package.read(name))


def test_write_idml_references_native_spreads_stories_and_colors(tmp_path: Path) -> None:
    spec_path = tmp_path / "build.py"
    _write_spec(spec_path)

    target = write_idml(_document(spec_path), tmp_path / "out")

    with zipfile.ZipFile(target) as package:
        designmap = package.read("designmap.xml").decode()
        graphic = package.read("Resources/Graphic.xml").decode()
        spread_name = next(
            name for name in package.namelist() if name.startswith("Spreads/Spread_")
        )
        story_name = next(name for name in package.namelist() if name.startswith("Stories/Story_"))
        spread = package.read(spread_name).decode()
        story = package.read(story_name).decode()

    story_id = story_name.removeprefix("Stories/Story_").removesuffix(".xml")
    assert 'Value="native-editable-mvp"' in designmap
    assert f'src="{spread_name}"' in designmap
    assert f'src="{story_name}"' in designmap
    assert 'Name="bg"' in spread
    assert '<Rectangle ' in spread
    assert 'Name="headline"' in spread
    assert '<TextFrame ' in spread
    assert f'ParentStory="{story_id}"' in spread
    assert 'Name="rule"' in spread
    assert '<GraphicLine ' in spread
    assert '<Content>Hello</Content>' in story
    assert 'Folio_112233' in graphic


def test_build_idml_target_writes_native_package(tmp_path: Path) -> None:
    spec_path = tmp_path / "build.py"
    _write_spec(spec_path)
    out_dir = tmp_path / "out"

    command = runner.invoke(
        app,
        [
            "build",
            str(spec_path),
            "idml",
            "--out-dir",
            str(out_dir),
            "--no-cache",
        ],
    )

    assert command.exit_code == 0, command.stdout
    assert not (out_dir / "cover.svg").exists()
    assert not (out_dir / "inside.svg").exists()
    assert (out_dir / "folio.idml").exists()
    assert not (out_dir / "Links").exists()
    assert "folio.idml" in command.stdout


def test_build_idml_target_writes_one_package_per_document(tmp_path: Path) -> None:
    spec_path = tmp_path / "build.py"
    spec_path.write_text(
        dedent(
            """
            from folio.dsl import collection, document, idml, page, rect, text

            def build():
                return collection(
                    document(
                        "brochure",
                        pages=[
                            page(
                                rect("brochure_bg", 0, 0, 100, 50, fill="#ffffff"),
                                text("brochure_title", 10, 20, "Brochure", size_pt=12),
                                page_id="brochure-cover",
                                filename="brochure-cover.svg",
                                page_number=1,
                                width_mm=100,
                                height_mm=50,
                            )
                        ],
                        filename="TM42_brochure",
                        title="TM42 Brochure",
                        export_presets=[idml()],
                        default_exports=["idml"],
                    ),
                    document(
                        "tv",
                        pages=[
                            page(
                                rect("tv_bg", 0, 0, 192, 108, fill="#ffffff"),
                                text("tv_title", 10, 20, "TV", size_pt=12),
                                page_id="tv",
                                filename="tv.svg",
                                page_number=1,
                                width_mm=192,
                                height_mm=108,
                            )
                        ],
                        filename="TM42_tv_16x9",
                        title="TM42 TV 16:9",
                        export_presets=[idml()],
                        default_exports=["idml"],
                    ),
                )
            """
        ).strip()
        + "\n",
        encoding="utf-8",
    )
    out_dir = tmp_path / "out"

    command = runner.invoke(
        app,
        [
            "build",
            str(spec_path),
            "idml",
            "--out-dir",
            str(out_dir),
            "--no-cache",
        ],
    )

    assert command.exit_code == 0, command.stdout
    assert not (out_dir / "brochure-cover.svg").exists()
    assert not (out_dir / "tv.svg").exists()
    assert (out_dir / "TM42_brochure.idml").exists()
    assert (out_dir / "TM42_tv_16x9.idml").exists()
    assert not (out_dir / "folio.idml").exists()


def test_build_idml_target_rejects_page_filter(tmp_path: Path) -> None:
    spec_path = tmp_path / "build.py"
    _write_spec(spec_path)
    out_dir = tmp_path / "out"

    command = runner.invoke(
        app,
        [
            "build",
            str(spec_path),
            "idml",
            "--page",
            "2",
            "--out-dir",
            str(out_dir),
            "--no-cache",
        ],
    )

    assert command.exit_code == 2
    assert "--page applies only to page-scoped export targets" in command.stdout


def test_build_rejects_unknown_target(tmp_path: Path) -> None:
    spec_path = tmp_path / "build.py"
    _write_spec(spec_path)

    command = runner.invoke(app, ["build", str(spec_path), "missing"])

    assert command.exit_code == 2
