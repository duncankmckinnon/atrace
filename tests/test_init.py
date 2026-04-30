from __future__ import annotations

import importlib
import subprocess
import sys
from pathlib import Path


def test_atrace_is_importable():
    import atrace
    assert atrace is not None


def test_version_is_string():
    import atrace
    assert isinstance(atrace.__version__, str)


def test_version_value():
    import atrace
    assert atrace.__version__ == "0.1.0"


def test_version_matches_pyproject(tmp_path):
    """Version in __init__.py must match pyproject.toml."""
    import tomllib

    import atrace

    repo_root = Path(__file__).resolve().parent.parent
    pyproject = repo_root / "pyproject.toml"
    with open(pyproject, "rb") as f:
        data = tomllib.load(f)
    assert data["project"]["version"] == atrace.__version__


def test_pyproject_name():
    import tomllib

    repo_root = Path(__file__).resolve().parent.parent
    with open(repo_root / "pyproject.toml", "rb") as f:
        data = tomllib.load(f)
    assert data["project"]["name"] == "atrace"


def test_pyproject_requires_python():
    import tomllib

    repo_root = Path(__file__).resolve().parent.parent
    with open(repo_root / "pyproject.toml", "rb") as f:
        data = tomllib.load(f)
    assert data["project"]["requires-python"] == ">=3.11"


def test_pyproject_entrypoint():
    import tomllib

    repo_root = Path(__file__).resolve().parent.parent
    with open(repo_root / "pyproject.toml", "rb") as f:
        data = tomllib.load(f)
    assert data["project"]["scripts"]["atrace"] == "atrace.cli:main"


def test_pyproject_runtime_dependencies():
    """All four required runtime deps must be declared with minimum versions."""
    import tomllib

    repo_root = Path(__file__).resolve().parent.parent
    with open(repo_root / "pyproject.toml", "rb") as f:
        data = tomllib.load(f)
    deps = data["project"]["dependencies"]
    dep_names = [d.split(">=")[0].split(">")[0].split("==")[0].strip() for d in deps]
    assert "click" in dep_names
    assert "msgpack" in dep_names
    assert "zstandard" in dep_names
    assert "pyaml" in dep_names


def test_pyproject_dev_dependencies():
    import tomllib

    repo_root = Path(__file__).resolve().parent.parent
    with open(repo_root / "pyproject.toml", "rb") as f:
        data = tomllib.load(f)
    dev_deps = data["dependency-groups"]["dev"]
    dev_names = [d.split(">=")[0].split(">")[0].split("==")[0].strip() for d in dev_deps]
    assert "pytest" in dev_names


def test_pyproject_setuptools_src_layout():
    import tomllib

    repo_root = Path(__file__).resolve().parent.parent
    with open(repo_root / "pyproject.toml", "rb") as f:
        data = tomllib.load(f)
    find_cfg = data["tool"]["setuptools"]["packages"]["find"]
    assert find_cfg["where"] == ["src"]


def test_package_layout_init_exists():
    repo_root = Path(__file__).resolve().parent.parent
    assert (repo_root / "src" / "atrace" / "__init__.py").is_file()


def test_package_layout_main_exists():
    repo_root = Path(__file__).resolve().parent.parent
    assert (repo_root / "src" / "atrace" / "__main__.py").is_file()


def test_python_m_atrace_version():
    """Running `python -m atrace --version` should print the version."""
    result = subprocess.run(
        [sys.executable, "-m", "atrace", "--version"],
        capture_output=True,
        text=True,
        timeout=10,
    )
    assert result.returncode == 0
    assert "0.1.0" in result.stdout
