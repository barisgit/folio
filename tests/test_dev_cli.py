"""CLI tests for `folio dev`."""

from __future__ import annotations

from pathlib import Path

from typer.testing import CliRunner

from folio.cli import app

runner = CliRunner()


class _FakeServer:
    server_address = ("127.0.0.1", 4242)

    def __init__(self) -> None:
        self.served = False
        self.closed = False

    def serve_forever(self) -> None:
        self.served = True

    def server_close(self) -> None:
        self.closed = True


def test_dev_help_includes_host_port_and_open_flags() -> None:
    result = runner.invoke(app, ["dev", "--help"])

    assert result.exit_code == 0
    assert "--host" in result.stdout
    assert "--port" in result.stdout
    assert "--open" in result.stdout
    assert "--no-open" in result.stdout


def test_dev_invalid_spec_exits_nonzero(tmp_path: Path) -> None:
    result = runner.invoke(app, ["dev", str(tmp_path / "missing.py"), "--no-open"])

    assert result.exit_code == 1
    assert "Dev server error" in result.stdout
    assert "DSL file not found" in result.stdout


def test_dev_command_reports_url_and_ignores_browser_open_failure(
    tmp_path: Path,
    monkeypatch,
) -> None:
    spec_path = tmp_path / "build.py"
    spec_path.write_text("# fake; server creation is monkeypatched\n", encoding="utf-8")
    fake_server = _FakeServer()
    opened: list[str] = []

    def fake_create(resolved_spec: Path, *, host: str, port: int) -> _FakeServer:
        assert resolved_spec == spec_path.resolve()
        assert host == "127.0.0.1"
        assert port == 0
        return fake_server

    def fake_open(url: str) -> bool:
        opened.append(url)
        raise RuntimeError("no browser")

    monkeypatch.setattr("folio.cli.dev.create_playground_server", fake_create)
    monkeypatch.setattr("folio.cli.dev.webbrowser.open", fake_open)

    result = runner.invoke(app, ["dev", str(spec_path), "--open"])

    assert result.exit_code == 0
    assert "Serving Folio playground at http://127.0.0.1:4242/" in result.stdout
    assert opened == ["http://127.0.0.1:4242/"]
    assert fake_server.served is True
    assert fake_server.closed is True
