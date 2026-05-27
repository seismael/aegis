import os
import shutil
from pathlib import Path

import pytest

from aegis.domain.evaluation.scorecard import Scorecard


@pytest.fixture
def local_tmp_path():
    path = os.path.abspath(".test_tmp")
    if os.path.exists(path):
        shutil.rmtree(path)
    os.makedirs(path)
    yield path
    shutil.rmtree(path)


def test_scorecard_health_calculation(local_tmp_path):
    root = local_tmp_path
    service = Scorecard(root)
    # Mock data: 10 rules, 2 active violations
    content = service.generate(
        rules=[{"id": str(i)} for i in range(10)],
        violations=[{"rule_id": "0"}, {"rule_id": "1"}],
        exceptions=[],
    )
    assert "Health Score: 80%" in content


def test_scorecard_health_clamping(local_tmp_path):
    root = local_tmp_path
    service = Scorecard(root)
    # 5 rules, 10 violations -> health should be 0, not negative
    content = service.generate(
        rules=[{"id": str(i)} for i in range(5)],
        violations=[{"rule_id": str(i)} for i in range(10)],
        exceptions=[],
    )
    assert "Health Score: 0%" in content


def test_scorecard_sync_to_disk(local_tmp_path):
    root = local_tmp_path
    service = Scorecard(root)
    content = "# Test Scorecard"
    service.sync_to_disk(content)

    expected_path = Path(root) / "AEGIS.md"
    assert expected_path.exists()
    assert expected_path.read_text(encoding="utf-8") == content


def test_scorecard_with_objects(local_tmp_path):
    class MockRule:
        def __init__(self, id):
            self.id = id

    root = local_tmp_path
    service = Scorecard(root)
    content = service.generate(
        rules=[MockRule("rule-1")], violations=[], exceptions=["debt-1"]
    )
    assert "- rule-1" in content
    assert "Exceptions (Technical Debt)" in content
    assert "- debt-1" in content
