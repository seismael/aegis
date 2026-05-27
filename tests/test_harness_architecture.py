from pathlib import Path

import pytest

from aegis.infrastructure.harnesses.base import BaseHarness


def test_harness_interface_cannot_be_instantiated():
    with pytest.raises(TypeError):
        BaseHarness(Path("/tmp"))


def test_harness_subclass_must_implement_all_methods():
    class IncompleteHarness(BaseHarness):
        @property
        def name(self) -> str:
            return "incomplete"

    with pytest.raises(TypeError):
        IncompleteHarness(Path("/tmp"))


def test_complete_harness_can_be_instantiated():
    class CompleteHarness(BaseHarness):
        def install(self) -> list[str]:
            return []

        def deploy_skills(self) -> list[str]:
            return []

        def deploy_workspace_instructions(self, workspace_root: str) -> list[str]:
            return []

        @property
        def name(self) -> str:
            return "complete"

    harness = CompleteHarness(Path("/tmp"))
    assert harness.name == "complete"
    assert harness.home == Path("/tmp")
