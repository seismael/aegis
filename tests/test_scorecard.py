import os
import shutil
import pytest
from aegis.domain.evaluation.scorecard import ScorecardService

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
    service = ScorecardService(root)
    # Mock data: 10 rules, 2 active violations
    content = service.generate(
        rules=[{"id": str(i)} for i in range(10)],
        violations=[{"rule_id": "0"}, {"rule_id": "1"}],
        exceptions=[]
    )
    assert "Health Score: 80%" in content

def test_scorecard_sync_to_disk(local_tmp_path):
    root = local_tmp_path
    service = ScorecardService(root)
    content = "# Test Scorecard"
    service.sync_to_disk(content)
    
    expected_path = os.path.join(root, "AEGIS.md")
    assert os.path.exists(expected_path)
    with open(expected_path, "r", encoding="utf-8") as f:
        assert f.read() == content

def test_scorecard_with_objects(local_tmp_path):
    class MockRule:
        def __init__(self, id):
            self.id = id
            
    root = local_tmp_path
    service = ScorecardService(root)
    content = service.generate(
        rules=[MockRule("rule-1")],
        violations=[],
        exceptions=["debt-1"]
    )
    assert "- rule-1" in content
    assert "Exceptions (Technical Debt)" in content
    assert "- debt-1" in content
