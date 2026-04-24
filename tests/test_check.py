"""Tests for `folio check`."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock

import pytest
from typer.testing import CliRunner

from folio.check.backends import (
    FORMAT_BACKENDS,
    LINT_BACKENDS,
    TYPECHECK_BACKENDS,
    BackendResult,
    BlackFormatBackend,
    PyrightTypecheckBackend,
    RuffFormatBackend,
    RuffLintBackend,
    TyTypecheckBackend,
    select_backend,
)
from folio.check.runner import EXIT_DIAGNOSTICS, EXIT_INFRA_FAILURE, EXIT_PASS, run_check
from folio.check.target import CheckTarget, resolve_check_target
from folio.cli import app

runner = CliRunner()


def _success_backend(name: str = "mock") -> MagicMock:
    backend = MagicMock()
    backend.name = name
    backend.is_available.return_value = True
    backend.run.return_value = BackendResult(success=True, output="", backend_name=name)
    return backend


def _success_step(runner_mod):
    return runner_mod.StepResult(label="validate", success=True)


class TestResolveCheckTarget:
    def test_none_resolves_to_cwd(
        self,
        tmp_path: Path,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        monkeypatch.chdir(tmp_path)
        (tmp_path / "build.py").write_text("# spec\n")

        target = resolve_check_target(None)

        assert target.spec_path == tmp_path / "build.py"
        assert target.project_root == tmp_path

    def test_dir_resolves_to_dir_build_py(self, tmp_path: Path) -> None:
        (tmp_path / "build.py").write_text("# spec\n")

        target = resolve_check_target(tmp_path)

        assert target.spec_path == tmp_path / "build.py"
        assert target.project_root == tmp_path

    def test_file_resolves_to_parent(self, tmp_path: Path) -> None:
        spec = tmp_path / "custom.py"
        spec.write_text("# spec\n")

        target = resolve_check_target(spec)

        assert target.spec_path == spec
        assert target.project_root == tmp_path


class TestSelectBackend:
    def test_returns_first_available(self) -> None:
        first = MagicMock()
        first.name = "first"
        first.is_available.return_value = True

        result = select_backend([first])

        assert result is not None
        assert result.backend is first
        assert result.skipped == []

    def test_falls_back_on_unavailable(self) -> None:
        unavailable = MagicMock()
        unavailable.name = "unavailable"
        unavailable.is_available.return_value = False
        available = MagicMock()
        available.name = "available"
        available.is_available.return_value = True

        result = select_backend([unavailable, available])

        assert result is not None
        assert result.backend is available
        assert result.skipped == ["unavailable"]

    def test_returns_none_when_all_unavailable(self) -> None:
        first = MagicMock()
        first.name = "a"
        first.is_available.return_value = False
        second = MagicMock()
        second.name = "b"
        second.is_available.return_value = False

        assert select_backend([first, second]) is None


class TestFallbackChains:
    def test_lint_uses_only_ruff(self) -> None:
        assert len(LINT_BACKENDS) == 1
        assert isinstance(LINT_BACKENDS[0], RuffLintBackend)

    def test_format_uses_ruff_then_black(self) -> None:
        assert len(FORMAT_BACKENDS) == 2
        assert isinstance(FORMAT_BACKENDS[0], RuffFormatBackend)
        assert isinstance(FORMAT_BACKENDS[1], BlackFormatBackend)

    def test_typecheck_uses_ty_then_pyright(self) -> None:
        assert len(TYPECHECK_BACKENDS) == 2
        assert isinstance(TYPECHECK_BACKENDS[0], TyTypecheckBackend)
        assert isinstance(TYPECHECK_BACKENDS[1], PyrightTypecheckBackend)


class TestRunnerBehavior:
    def test_validate_accepts_document_collection(self, tmp_path: Path) -> None:
        from folio.check import runner as runner_mod

        spec_path = tmp_path / "build.py"
        spec_path.write_text(
            """
from folio.dsl import collection, document, page, rect


def build():
    return collection(
        document(
            "one",
            pages=[page(rect("one_bg", 0, 0, 10, 10), page_id="one", filename="one.svg")],
        ),
        document(
            "two",
            pages=[page(rect("two_bg", 0, 0, 10, 10), page_id="two", filename="two.svg")],
        ),
    )
""".strip()
            + "\n",
            encoding="utf-8",
        )
        target = CheckTarget(spec_path=spec_path, project_root=tmp_path)

        result = runner_mod.run_validate(target)

        assert result.success

    def test_first_backend_with_diagnostics_stops_fallback(
        self,
        tmp_path: Path,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        from folio.check import runner as runner_mod

        first = MagicMock()
        first.name = "first"
        first.is_available.return_value = True
        first.run.return_value = BackendResult(
            success=False,
            output="1 lint issue(s) found",
            backend_name="first",
            diagnostics_count=1,
        )
        second = _success_backend("second")
        noop = _success_backend("noop")

        monkeypatch.setattr(runner_mod, "LINT_BACKENDS", [first, second])
        monkeypatch.setattr(runner_mod, "FORMAT_BACKENDS", [noop])
        monkeypatch.setattr(runner_mod, "TYPECHECK_BACKENDS", [noop])
        monkeypatch.setattr(
            runner_mod,
            "run_validate",
            lambda *args, **kwargs: _success_step(runner_mod),
        )

        target = CheckTarget(spec_path=tmp_path / "build.py", project_root=tmp_path)
        (tmp_path / "build.py").write_text("# ok\n")

        result = run_check(target)

        first.run.assert_called_once()
        second.run.assert_not_called()
        assert not result.ok
        assert result.exit_code == EXIT_DIAGNOSTICS

    def test_fix_enables_format_step(
        self,
        tmp_path: Path,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        from folio.check import runner as runner_mod

        ok_backend = _success_backend("ok")
        monkeypatch.setattr(runner_mod, "LINT_BACKENDS", [ok_backend])
        monkeypatch.setattr(runner_mod, "FORMAT_BACKENDS", [ok_backend])
        monkeypatch.setattr(runner_mod, "TYPECHECK_BACKENDS", [ok_backend])
        monkeypatch.setattr(
            runner_mod,
            "run_validate",
            lambda *args, **kwargs: _success_step(runner_mod),
        )

        target = CheckTarget(spec_path=tmp_path / "build.py", project_root=tmp_path)
        (tmp_path / "build.py").write_text("# ok\n")

        without_fix = run_check(target, fmt=False, fix=False)
        with_fix = run_check(target, fmt=False, fix=True)

        assert "format" not in [step.label for step in without_fix.steps]
        assert "format" in [step.label for step in with_fix.steps]

    def test_validate_failure_stops_pipeline(
        self,
        tmp_path: Path,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        from folio.check import runner as runner_mod

        lint_backend = _success_backend("lint")
        monkeypatch.setattr(runner_mod, "LINT_BACKENDS", [lint_backend])
        monkeypatch.setattr(
            runner_mod,
            "run_validate",
            lambda *args, **kwargs: runner_mod.StepResult(
                label="validate",
                success=False,
                output="bad spec",
            ),
        )

        target = CheckTarget(spec_path=tmp_path / "build.py", project_root=tmp_path)

        result = run_check(target)

        assert len(result.steps) == 1
        assert result.steps[0].label == "validate"
        assert not result.steps[0].success
        lint_backend.run.assert_not_called()

    def test_fix_is_forwarded_to_lint_backend(
        self,
        tmp_path: Path,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        from folio.check import runner as runner_mod

        lint_backend = _success_backend("lint")
        ok_backend = _success_backend("ok")
        monkeypatch.setattr(runner_mod, "LINT_BACKENDS", [lint_backend])
        monkeypatch.setattr(runner_mod, "FORMAT_BACKENDS", [ok_backend])
        monkeypatch.setattr(runner_mod, "TYPECHECK_BACKENDS", [ok_backend])
        monkeypatch.setattr(
            runner_mod,
            "run_validate",
            lambda *args, **kwargs: _success_step(runner_mod),
        )

        target = CheckTarget(spec_path=tmp_path / "build.py", project_root=tmp_path)
        (tmp_path / "build.py").write_text("# ok\n")

        run_check(target, fix=True)

        lint_backend.run.assert_called_once()
        assert lint_backend.run.call_args.kwargs["fix"] is True


class TestCLIOutput:
    def test_cli_pass_output_is_concise(
        self,
        tmp_path: Path,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        from folio.check import runner as runner_mod

        ok_backend = _success_backend("mock")
        monkeypatch.setattr(runner_mod, "LINT_BACKENDS", [ok_backend])
        monkeypatch.setattr(runner_mod, "FORMAT_BACKENDS", [ok_backend])
        monkeypatch.setattr(runner_mod, "TYPECHECK_BACKENDS", [ok_backend])
        monkeypatch.setattr(
            runner_mod,
            "run_validate",
            lambda *args, **kwargs: _success_step(runner_mod),
        )

        (tmp_path / "build.py").write_text("# ok\n")
        result = runner.invoke(app, ["check", str(tmp_path)])

        assert result.exit_code == EXIT_PASS
        for line in result.output.strip().splitlines():
            assert line.startswith("✓") or line.strip() == ""
            assert "$ " not in line

    def test_cli_verbose_includes_selected_command(
        self,
        tmp_path: Path,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        from folio.check import runner as runner_mod

        backend = _success_backend("mock")
        backend.run.return_value = BackendResult(
            success=True,
            output="backend output",
            backend_name="mock",
            command=("mock-tool", "check", str(tmp_path)),
        )
        monkeypatch.setattr(runner_mod, "LINT_BACKENDS", [backend])
        monkeypatch.setattr(runner_mod, "FORMAT_BACKENDS", [backend])
        monkeypatch.setattr(runner_mod, "TYPECHECK_BACKENDS", [backend])
        monkeypatch.setattr(
            runner_mod,
            "run_validate",
            lambda *args, **kwargs: _success_step(runner_mod),
        )

        (tmp_path / "build.py").write_text("# ok\n")
        result = runner.invoke(app, ["check", str(tmp_path), "--verbose"])

        assert result.exit_code == EXIT_PASS
        assert "$ mock-tool check" in result.output
        assert "backend output" in result.output

    def test_check_help_is_registered(self) -> None:
        result = runner.invoke(app, ["check", "--help"])

        assert result.exit_code == 0
        assert "Validate, lint, and typecheck" in result.output

    def test_check_appears_in_main_help(self) -> None:
        result = runner.invoke(app, ["--help"])

        assert "check" in result.output


class TestExitCodes:
    def test_pass_returns_0(
        self,
        tmp_path: Path,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        from folio.check import runner as runner_mod

        ok_backend = _success_backend("mock")
        monkeypatch.setattr(runner_mod, "LINT_BACKENDS", [ok_backend])
        monkeypatch.setattr(runner_mod, "FORMAT_BACKENDS", [ok_backend])
        monkeypatch.setattr(runner_mod, "TYPECHECK_BACKENDS", [ok_backend])
        monkeypatch.setattr(
            runner_mod,
            "run_validate",
            lambda *args, **kwargs: _success_step(runner_mod),
        )

        (tmp_path / "build.py").write_text("# ok\n")
        result = runner.invoke(app, ["check", str(tmp_path)])

        assert result.exit_code == EXIT_PASS

    def test_diagnostics_returns_1(
        self,
        tmp_path: Path,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        from folio.check import runner as runner_mod

        fail_backend = _success_backend("mock-lint")
        fail_backend.run.return_value = BackendResult(
            success=False,
            output="1 lint issue(s) found",
            backend_name="mock-lint",
            diagnostics_count=1,
        )
        ok_backend = _success_backend("ok")
        monkeypatch.setattr(runner_mod, "LINT_BACKENDS", [fail_backend])
        monkeypatch.setattr(runner_mod, "FORMAT_BACKENDS", [ok_backend])
        monkeypatch.setattr(runner_mod, "TYPECHECK_BACKENDS", [ok_backend])
        monkeypatch.setattr(
            runner_mod,
            "run_validate",
            lambda *args, **kwargs: _success_step(runner_mod),
        )

        (tmp_path / "build.py").write_text("# ok\n")
        result = runner.invoke(app, ["check", str(tmp_path)])

        assert result.exit_code == EXIT_DIAGNOSTICS

    def test_infra_failure_returns_2(
        self,
        tmp_path: Path,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        from folio.check import runner as runner_mod

        unavailable = MagicMock()
        unavailable.name = "unavailable"
        unavailable.is_available.return_value = False
        monkeypatch.setattr(runner_mod, "LINT_BACKENDS", [unavailable])
        monkeypatch.setattr(runner_mod, "FORMAT_BACKENDS", [unavailable])
        monkeypatch.setattr(runner_mod, "TYPECHECK_BACKENDS", [unavailable])
        monkeypatch.setattr(
            runner_mod,
            "run_validate",
            lambda *args, **kwargs: _success_step(runner_mod),
        )

        (tmp_path / "build.py").write_text("# ok\n")
        result = runner.invoke(app, ["check", str(tmp_path)])

        assert result.exit_code == EXIT_INFRA_FAILURE
