from pathlib import Path

import pytest

from aegis.infrastructure.harnesses.base import BaseHarness


def test_harness_interface_cannot_be_instantiated():
    with pytest.raises(TypeError):
        BaseHarness()


def test_harness_subclass_must_implement_all_methods():
    class IncompleteHarness(BaseHarness):
        @property
        def name(self) -> str:
            return "incomplete"

    with pytest.raises(TypeError):
        IncompleteHarness()


def test_complete_harness_can_be_instantiated():
    class CompleteHarness(BaseHarness):
        def install_local(self, workspace_root: Path) -> list[str]:
            return []

        def deploy_skills_local(self, workspace_root: Path) -> list[str]:
            return []

        def deploy_workspace_instructions(self, workspace_root: str) -> list[str]:
            return []

        @property
        def name(self) -> str:
            return "complete"

    harness = CompleteHarness()
    assert harness.name == "complete"
