from __future__ import annotations

import json
import shutil
import subprocess
import tarfile
from pathlib import Path

import pytest  # noqa: F401

REPO_ROOT = Path(__file__).resolve().parent.parent
INDEX_RELPATH = Path("src/folio/services/docs/index.json")


@pytest.fixture
def repo_copy(tmp_path: Path) -> Path:
    """Copy the repo (minus heavy build detritus) into a tmp dir."""
    destination = tmp_path / "folio"
    shutil.copytree(
        REPO_ROOT,
        destination,
        ignore=shutil.ignore_patterns(
            ".git",
            ".venv",
            "dist",
            "build",
            "__pycache__",
            "*.egg-info",
            ".folio-cache",
            ".pytest_cache",
            ".ruff_cache",
        ),
        symlinks=False,
    )
    return destination


def _uv_binary() -> str:
    path = shutil.which("uv")
    if not path:
        pytest.skip("uv is required to exercise the Hatch build hook in isolation")
    return path


def _run_build(cwd: Path) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [_uv_binary(), "build", "--sdist"],
        cwd=cwd,
        capture_output=True,
        text=True,
        check=False,
    )


def test_sdist_contains_current_index(repo_copy: Path) -> None:
    result = _run_build(repo_copy)
    assert result.returncode == 0, f"sdist build failed:\n{result.stderr}"
    sdist_paths = list((repo_copy / "dist").glob("*.tar.gz"))
    assert sdist_paths, "sdist was not produced"
    committed = (repo_copy / INDEX_RELPATH).read_bytes()
    with tarfile.open(sdist_paths[0], "r:gz") as tf:
        inner = next(
            member
            for member in tf.getmembers()
            if member.name.endswith("/src/folio/services/docs/index.json")
        )
        fobj = tf.extractfile(inner)
        assert fobj is not None
        bundled = fobj.read()
    assert bundled == committed, "sdist ships an index that does not match the committed file"


def test_stale_committed_index_fails_build(repo_copy: Path) -> None:
    index_path = repo_copy / INDEX_RELPATH
    payload = json.loads(index_path.read_text(encoding="utf-8"))
    payload["symbols"][0]["summary"] = "STALE-FOR-TEST"
    index_path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")

    result = _run_build(repo_copy)
    assert result.returncode != 0, "build must fail on a stale committed index"
    combined = result.stdout + result.stderr
    assert "python -m folio.services.docs.generate" in combined, (
        f"staleness error message missing regeneration hint:\n{combined}"
    )


def test_build_hook_does_not_mutate_source(repo_copy: Path) -> None:
    before = (repo_copy / INDEX_RELPATH).read_bytes()
    result = _run_build(repo_copy)
    assert result.returncode == 0, result.stderr
    after = (repo_copy / INDEX_RELPATH).read_bytes()
    assert before == after, "build hook mutated the committed index"
