from __future__ import annotations

from pathlib import Path

import pytest
from typer.testing import CliRunner

from folio.cli import app
from folio.skill import skill_root

runner = CliRunner()


def test_project_scope_install_writes_into_cwd(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.chdir(tmp_path)
    result = runner.invoke(app, ["skill", "install", "--scope", "project"])
    assert result.exit_code == 0, result.output
    destination = tmp_path / ".agents" / "skills" / "folio"
    assert (destination / "SKILL.md").is_file()
    assert str(destination.resolve()) in result.output


def test_user_scope_install_uses_home(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    fake_home = tmp_path / "home"
    fake_home.mkdir()
    monkeypatch.setattr(Path, "home", lambda: fake_home)
    result = runner.invoke(app, ["skill", "install", "--scope", "user"])
    assert result.exit_code == 0, result.output
    destination = fake_home / ".agents" / "skills" / "folio"
    assert (destination / "SKILL.md").is_file()


def test_default_scope_is_project(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.chdir(tmp_path)
    result = runner.invoke(app, ["skill", "install"])
    assert result.exit_code == 0, result.output
    assert (tmp_path / ".agents" / "skills" / "folio" / "SKILL.md").is_file()


def test_idempotent_reinstall_exits_zero(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.chdir(tmp_path)
    first = runner.invoke(app, ["skill", "install"])
    assert first.exit_code == 0
    second = runner.invoke(app, ["skill", "install"])
    assert second.exit_code == 0, second.output


def test_conflict_without_force_exits_three(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.chdir(tmp_path)
    destination = tmp_path / ".agents" / "skills" / "folio"
    destination.mkdir(parents=True)
    (destination / "SKILL.md").write_text("custom content that does not match\n")
    result = runner.invoke(app, ["skill", "install"])
    assert result.exit_code == 3
    assert "conflicting" in result.output.lower()


def test_force_overwrites_conflicts(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.chdir(tmp_path)
    destination = tmp_path / ".agents" / "skills" / "folio"
    destination.mkdir(parents=True)
    (destination / "SKILL.md").write_text("divergent\n")
    result = runner.invoke(app, ["skill", "install", "--force"])
    assert result.exit_code == 0, result.output
    expected = (skill_root() / "SKILL.md").read_bytes()
    assert (destination / "SKILL.md").read_bytes() == expected


def test_prints_absolute_destination(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.chdir(tmp_path)
    result = runner.invoke(app, ["skill", "install"])
    assert result.exit_code == 0
    printed = result.output.strip().splitlines()[-1]
    assert Path(printed).is_absolute()
    assert printed.endswith(".agents/skills/folio")
