import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))
sys.path.insert(0, str(HERE))

import pytest  # noqa: E402


@pytest.fixture(autouse=True)
def _fresh_last_messages(monkeypatch):
    """Each test starts with nothing remembered for the Last message column
    (#146): no cached transcript ends, no sessions known to have none."""
    from thechatplace import hub
    from thechatplace.transcript import LastMessages
    monkeypatch.setattr(hub, "LAST_MESSAGES", LastMessages())
    monkeypatch.setattr(hub, "_NO_TRANSCRIPT", {})
