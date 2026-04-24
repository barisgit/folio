from __future__ import annotations

import json
from pathlib import Path

import pytest

from folio.services.check.runner import run_examples
from folio.services.check.target import CheckTarget


@pytest.fixture
def target(tmp_path: Path) -> CheckTarget:
    spec = tmp_path / "build.py"
    spec.write_text("# stub\n")
    return CheckTarget(spec_path=spec, project_root=tmp_path)


def test_examples_step_passes_on_packaged_index(target: CheckTarget) -> None:
    result = run_examples(target)
    assert result.success, result.output
    assert result.label == "examples"


def test_examples_step_reports_failure_labels(
    target: CheckTarget, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    payload = {
        "version": 1,
        "symbols": [
            {
                "id": "test.broken",
                "examples": [
                    {"code": "raise ValueError('boom')", "caption": None, "setup": None}
                ],
            }
        ],
    }
    index_file = tmp_path / "broken_index.json"
    index_file.write_text(json.dumps(payload), encoding="utf-8")

    from folio.services.check import runner as runner_mod

    monkeypatch.setattr(
        "folio.services.docs.generate.index_path", lambda: index_file
    )
    _ = runner_mod

    result = run_examples(target)
    assert not result.success
    assert "test.broken[1]" in result.output
    assert "ValueError" in result.output


def test_examples_step_uses_setup_when_provided(
    target: CheckTarget, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    payload = {
        "version": 1,
        "symbols": [
            {
                "id": "test.with_setup",
                "examples": [
                    {
                        "code": "result = offset_value + 1",
                        "caption": None,
                        "setup": "offset_value = 10",
                    }
                ],
            }
        ],
    }
    index_file = tmp_path / "setup_index.json"
    index_file.write_text(json.dumps(payload), encoding="utf-8")

    monkeypatch.setattr("folio.services.docs.generate.index_path", lambda: index_file)

    result = run_examples(target)
    assert result.success, result.output


def test_examples_step_runs_between_validate_and_lint(
    target: CheckTarget, monkeypatch: pytest.MonkeyPatch
) -> None:
    from unittest.mock import MagicMock

    from folio.services.check import runner as runner_mod
    from folio.services.check.backends import BackendResult

    ok_backend = MagicMock()
    ok_backend.name = "mock"
    ok_backend.is_available.return_value = True
    ok_backend.run.return_value = BackendResult(
        success=True, output="", backend_name="mock"
    )
    monkeypatch.setattr(runner_mod, "LINT_BACKENDS", [ok_backend])
    monkeypatch.setattr(runner_mod, "FORMAT_BACKENDS", [ok_backend])
    monkeypatch.setattr(runner_mod, "TYPECHECK_BACKENDS", [ok_backend])
    monkeypatch.setattr(
        runner_mod,
        "run_validate",
        lambda *args, **kwargs: runner_mod.StepResult(label="validate", success=True),
    )

    result = runner_mod.run_check(target)
    labels = [step.label for step in result.steps]
    assert labels == ["validate", "examples", "lint", "typecheck"]
