import pytest


@pytest.fixture
def tracker_path(tmp_path):
    """Isolated tracker file path for each test — never touches the real file."""
    return str(tmp_path / "outreach_tracker.json")
