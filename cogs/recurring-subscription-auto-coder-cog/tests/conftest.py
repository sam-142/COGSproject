"""Tests run against the synthetic context in evaluation/fixtures/context/.

The Cog's own context/ files are empty defaults, so a real run uses only real
data. The tests need the invented vendors, rules and chart of accounts to exercise every case,
so for the test session DEFAULT_DIR points at a merged folder: context/ with
evaluation/fixtures/context/ laid over it.
"""
import shutil
from pathlib import Path

import pytest

from auto_coder import context

ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture(scope="session", autouse=True)
def synthetic_context(tmp_path_factory):
    # Session-wide, so it is in place before any module-scoped fixture runs.
    merged = tmp_path_factory.mktemp("context")
    for src in (ROOT / "context", ROOT / "evaluation" / "fixtures" / "context"):
        for f in src.iterdir():
            if f.suffix in (".yaml", ".md"):
                shutil.copy(f, merged / f.name)
    patch = pytest.MonkeyPatch()
    patch.setattr(context, "DEFAULT_DIR", merged)
    yield merged
    patch.undo()
