from pathlib import Path

import pytest


@pytest.fixture(scope="session")
def project_root() -> Path:
    """Returns the absolute path to the project root directory."""
    return Path(__file__).parent.parent.resolve()


@pytest.fixture(scope="session")
def test_data_dir(project_root: Path) -> Path:
    """Returns the path to the test data directory."""
    data_dir = project_root / "tests" / "data"
    data_dir.mkdir(exist_ok=True)
    return data_dir
