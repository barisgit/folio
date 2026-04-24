"""Backend adapters for lint, format, and typecheck tools."""

from __future__ import annotations

import json
import shutil
import subprocess
from dataclasses import dataclass, field
from pathlib import Path
from typing import Protocol


@dataclass(frozen=True)
class BackendResult:
    """Result from running a single backend."""

    success: bool
    output: str
    backend_name: str
    command: tuple[str, ...] = ()
    diagnostics_count: int = 0
    fixed_count: int = 0


class Backend(Protocol):
    """Protocol for a check backend."""

    name: str

    def is_available(self) -> bool: ...

    def run(
        self, project_root: Path, *, fix: bool = False, verbose: bool = False
    ) -> BackendResult: ...


@dataclass
class BackendSelection:
    """Result of selecting a backend from a fallback chain."""

    backend: Backend
    skipped: list[str] = field(default_factory=list)


def _tool_available(name: str) -> bool:
    return shutil.which(name) is not None


def _run_cmd(args: list[str], *, cwd: Path) -> subprocess.CompletedProcess[str]:
    return subprocess.run(args, cwd=cwd, capture_output=True, text=True)


def _combined_output(proc: subprocess.CompletedProcess[str]) -> str:
    parts = [part.strip() for part in (proc.stdout, proc.stderr) if part and part.strip()]
    return "\n".join(parts)


def _diagnostic_lines(raw: str) -> list[str]:
    return [line for line in raw.splitlines() if line.strip()]


def _summarise_ruff_json(raw: str) -> tuple[int, str]:
    """Parse `ruff check --output-format json` output."""
    try:
        items = json.loads(raw)
    except (json.JSONDecodeError, TypeError):
        text = raw.strip()
        return (0, text) if text else (0, "")
    if not isinstance(items, list):
        text = raw.strip()
        return (0, text) if text else (0, "")

    diagnostics = len(items)
    lines: list[str] = []
    for item in items:
        filename = item.get("filename", "?")
        location = item.get("location", {}) or {}
        row = location.get("row", "?")
        code = item.get("code", "?")
        message = item.get("message", "")
        lines.append(f"{filename}:{row}: {code} {message}")
    return diagnostics, "\n".join(lines)


def _count_format_candidates(raw: str, *, prefixes: tuple[str, ...]) -> int:
    count = 0
    for line in raw.splitlines():
        stripped = line.strip()
        if stripped.startswith(prefixes):
            count += 1
    return count


def _summarise_pyright_json(raw: str) -> tuple[int, str]:
    """Parse pyright JSON output into (error_count, summary_text)."""
    try:
        data = json.loads(raw)
    except (json.JSONDecodeError, TypeError):
        text = raw.strip()
        return (0, text) if text else (0, "")

    diagnostics = data.get("generalDiagnostics", []) or []
    lines: list[str] = []
    for diagnostic in diagnostics:
        filename = diagnostic.get("file", "?")
        start = (diagnostic.get("range", {}) or {}).get("start", {}) or {}
        row = start.get("line", 0) + 1 if isinstance(start.get("line"), int) else "?"
        severity = diagnostic.get("severity", "")
        message = diagnostic.get("message", "")
        lines.append(f"{filename}:{row}: {severity} {message}")
    return len(diagnostics), "\n".join(lines)


class RuffLintBackend:
    """Lint with Ruff."""

    name = "ruff"

    def is_available(self) -> bool:
        return _tool_available("ruff")

    def run(
        self, project_root: Path, *, fix: bool = False, verbose: bool = False
    ) -> BackendResult:
        args = ["ruff", "check", "--output-format", "json", str(project_root)]
        if fix:
            args.insert(2, "--fix")
        proc = _run_cmd(args, cwd=project_root)
        diagnostics, summary = _summarise_ruff_json(proc.stdout)
        extra = proc.stderr.strip()
        success = proc.returncode == 0

        output = ""
        if verbose:
            output = "\n".join(part for part in (summary, extra) if part)
        elif not success:
            output = f"{diagnostics or 1} lint issue(s) found"

        return BackendResult(
            success=success,
            output=output,
            backend_name=self.name,
            command=tuple(args),
            diagnostics_count=diagnostics,
        )


class RuffFormatBackend:
    """Format check/write with Ruff formatter."""

    name = "ruff format"

    def is_available(self) -> bool:
        return _tool_available("ruff")

    def run(
        self, project_root: Path, *, fix: bool = False, verbose: bool = False
    ) -> BackendResult:
        args = ["ruff", "format"]
        if not fix:
            args.append("--check")
        args.append(str(project_root))
        proc = _run_cmd(args, cwd=project_root)
        raw = _combined_output(proc)
        success = proc.returncode == 0

        output = ""
        if verbose:
            output = raw
        elif not success:
            file_count = _count_format_candidates(raw, prefixes=("Would reformat",))
            output = f"{file_count or 1} file(s) need formatting"

        return BackendResult(
            success=success,
            output=output,
            backend_name=self.name,
            command=tuple(args),
        )


class BlackFormatBackend:
    """Format check/write with Black."""

    name = "black"

    def is_available(self) -> bool:
        return _tool_available("black")

    def run(
        self, project_root: Path, *, fix: bool = False, verbose: bool = False
    ) -> BackendResult:
        args = ["black"]
        if not fix:
            args.extend(["--check", "--diff"])
        args.append(str(project_root))
        proc = _run_cmd(args, cwd=project_root)
        raw = _combined_output(proc)
        success = proc.returncode == 0

        output = ""
        if verbose:
            output = raw
        elif not success:
            file_count = _count_format_candidates(raw, prefixes=("would reformat",))
            output = f"{file_count or 1} file(s) need formatting"

        return BackendResult(
            success=success,
            output=output,
            backend_name=self.name,
            command=tuple(args),
        )


class TyTypecheckBackend:
    """Typecheck with ty."""

    name = "ty"

    def is_available(self) -> bool:
        return _tool_available("ty")

    def run(
        self, project_root: Path, *, fix: bool = False, verbose: bool = False
    ) -> BackendResult:
        _ = fix
        args = [
            "ty",
            "check",
            "--output-format",
            "concise",
            "--no-progress",
            str(project_root),
        ]
        proc = _run_cmd(args, cwd=project_root)
        raw = _combined_output(proc)
        diagnostics = len(_diagnostic_lines(raw))
        success = proc.returncode == 0

        output = ""
        if verbose:
            output = raw
        elif not success:
            output = f"{diagnostics or 1} typecheck finding(s)"

        return BackendResult(
            success=success,
            output=output,
            backend_name=self.name,
            command=tuple(args),
            diagnostics_count=diagnostics,
        )


class PyrightTypecheckBackend:
    """Typecheck with pyright."""

    name = "pyright"

    def is_available(self) -> bool:
        return _tool_available("pyright")

    def run(
        self, project_root: Path, *, fix: bool = False, verbose: bool = False
    ) -> BackendResult:
        _ = fix
        args = ["pyright", "--outputjson", str(project_root)]
        proc = _run_cmd(args, cwd=project_root)
        diagnostics, summary = _summarise_pyright_json(proc.stdout)
        extra = proc.stderr.strip()
        success = proc.returncode == 0

        output = ""
        if verbose:
            output = "\n".join(part for part in (summary, extra) if part)
        elif not success:
            output = f"{diagnostics or 1} typecheck error(s)"

        return BackendResult(
            success=success,
            output=output,
            backend_name=self.name,
            command=tuple(args),
            diagnostics_count=diagnostics,
        )


LINT_BACKENDS: list[Backend] = [RuffLintBackend()]
FORMAT_BACKENDS: list[Backend] = [RuffFormatBackend(), BlackFormatBackend()]
TYPECHECK_BACKENDS: list[Backend] = [TyTypecheckBackend(), PyrightTypecheckBackend()]


def select_backend(chain: list[Backend]) -> BackendSelection | None:
    """Return the first available backend from a fallback chain."""
    skipped: list[str] = []
    for backend in chain:
        if backend.is_available():
            return BackendSelection(backend=backend, skipped=skipped)
        skipped.append(backend.name)
    return None
