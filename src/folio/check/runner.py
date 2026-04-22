"""Orchestrator for `folio check`."""

from __future__ import annotations

from dataclasses import dataclass, field

from folio.check.backends import (
    FORMAT_BACKENDS,
    LINT_BACKENDS,
    TYPECHECK_BACKENDS,
    Backend,
    BackendResult,
    select_backend,
)
from folio.check.target import CheckTarget

EXIT_PASS = 0
EXIT_DIAGNOSTICS = 1
EXIT_INFRA_FAILURE = 2


@dataclass
class StepResult:
    """Result of a single pipeline step."""

    label: str
    success: bool
    output: str = ""
    backend_name: str = ""
    command: tuple[str, ...] = ()
    skipped_backends: list[str] = field(default_factory=list)
    infra_failure: bool = False


@dataclass
class CheckResult:
    """Aggregate result of the full check pipeline."""

    steps: list[StepResult] = field(default_factory=list)

    @property
    def ok(self) -> bool:
        return all(step.success for step in self.steps)

    @property
    def infra_failure(self) -> bool:
        return any(step.infra_failure for step in self.steps)

    @property
    def exit_code(self) -> int:
        if self.infra_failure:
            return EXIT_INFRA_FAILURE
        if self.ok:
            return EXIT_PASS
        return EXIT_DIAGNOSTICS


def run_validate(target: CheckTarget) -> StepResult:
    """Run Folio validation on the resolved spec path."""
    from folio.dsl.loader import DslError, load_dsl_module
    from folio.dsl.renderer import RenderError, document_from_module, validate_document

    try:
        module = load_dsl_module(target.spec_path)
        validate_document(document_from_module(module))
    except (DslError, RenderError) as exc:
        return StepResult(label="validate", success=False, output=str(exc))
    return StepResult(label="validate", success=True)


def _run_backend_step(
    label: str,
    chain: list[Backend],
    target: CheckTarget,
    *,
    fix: bool = False,
    verbose: bool = False,
) -> StepResult:
    selection = select_backend(chain)
    if selection is None:
        return StepResult(
            label=label,
            success=False,
            output=f"No {label} backend available",
            skipped_backends=[backend.name for backend in chain],
            infra_failure=True,
        )

    backend_result: BackendResult = selection.backend.run(
        target.project_root,
        fix=fix,
        verbose=verbose,
    )
    return StepResult(
        label=label,
        success=backend_result.success,
        output=backend_result.output,
        backend_name=backend_result.backend_name,
        command=backend_result.command,
        skipped_backends=selection.skipped,
    )


def run_check(
    target: CheckTarget,
    *,
    fmt: bool = False,
    fix: bool = False,
    verbose: bool = False,
) -> CheckResult:
    """Execute validate → lint → optional format → typecheck."""
    result = CheckResult()

    validate_step = run_validate(target)
    result.steps.append(validate_step)
    if not validate_step.success:
        return result

    result.steps.append(
        _run_backend_step("lint", LINT_BACKENDS, target, fix=fix, verbose=verbose)
    )

    if fmt or fix:
        result.steps.append(
            _run_backend_step("format", FORMAT_BACKENDS, target, fix=fix, verbose=verbose)
        )

    result.steps.append(
        _run_backend_step(
            "typecheck",
            TYPECHECK_BACKENDS,
            target,
            fix=False,
            verbose=verbose,
        )
    )

    return result
