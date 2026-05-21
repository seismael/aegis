"""
Comprehensive 'Jailbreak' Verification Suite for Aegis v3.0 Architectural Sandbox.
Empirically validates multi-tenancy, quarantine states, micro-context, and shell bypass mitigation.
"""

import json
import asyncio
import pytest
from pathlib import Path
from unittest.mock import MagicMock, AsyncMock, patch

from aegis.kernel.server import AegisKernel
from aegis.domain.evaluation.vfs import SpeculativeVFS
from aegis.domain.evaluation.ports import ArchitecturalViolation


@pytest.fixture
def kernel(tmp_path):
    """Hardened kernel instance with a real SpeculativeVFS."""
    k = AegisKernel()
    # Mock container to point to tmp_path
    mock_container = MagicMock()
    mock_container.workspace_root = str(tmp_path)
    mock_container.vfs = SpeculativeVFS(str(tmp_path))
    
    # Mock rules
    mock_rule = MagicMock()
    mock_rule.id = "test-rule"
    mock_rule.severity.value = "HIGH"
    mock_rule.mode.value = "block"
    mock_rule.category.value = "architecture"
    mock_rule.description = "Forbidden pattern"
    mock_container.load_rules.return_value = [mock_rule]
    
    k.container = mock_container
    return k


class TestSandboxHardening:
    """Tier 3: Absolute Enforcement Validation."""

    @pytest.mark.asyncio
    async def test_phase_3_1_multi_tenancy_isolation(self, kernel, tmp_path):
        """Verify that Agent A cannot see or commit Agent B's unverified changes."""
        vfs = kernel.container.vfs
        file_path = "domain.py"
        
        # Agent A stages a change
        vfs.stage_change(file_path, "agent_a_content", session_id="agent_a")
        
        # Agent B reads the same file
        # Should NOT see Agent A's change, should see disk or error
        with pytest.raises(FileNotFoundError):
            vfs.read(file_path, session_id="agent_b")
            
        # Agent A reads the same file
        assert vfs.read(file_path, session_id="agent_a") == "agent_a_content"

    @pytest.mark.asyncio
    async def test_phase_3_2_quarantine_state_persistence(self, kernel, tmp_path):
        """Verify that high-severity violations trigger Quarantine instead of hard-abort."""
        # Setup real VFS but mock evaluation logic
        mock_eval = MagicMock()
        
        # Mock a HIGH severity violation
        violation = ArchitecturalViolation(
            file="forbidden.py",
            line=1,
            rule_id="no-boto3",
            severity="HIGH",
            description="Cloud leak detected"
        )
        mock_eval.evaluate_file.return_value = [violation]
        mock_eval._get_file_content.return_value = "import boto3"
        
        # Inject mock via property override
        with patch.object(AegisKernel, "_evaluation_service", mock_eval):
            result = await kernel.aegis_write_file("forbidden.py", "import boto3", session_id="agent_x")
        
        assert "QUARANTINED" in result
        # Verify it IS staged in VFS but NOT on disk
        assert kernel.container.vfs.is_staged("forbidden.py", session_id="agent_x")
        assert kernel.container.vfs.is_quarantined("forbidden.py", session_id="agent_x")
        assert not (tmp_path / "forbidden.py").exists()

    @pytest.mark.asyncio
    async def test_phase_3_3_dna_compression_efficiency(self, kernel):
        """Verify that aegis_read_file returns Micro-Context instead of full Manifesto."""
        kernel.container.vfs.stage_change("test.py", "print('hello')", session_id="test")
        
        # Use AsyncMock for coroutines
        mock_context = AsyncMock()
        mock_context.return_value = json.dumps({
            "rules": [{"id": "rule1", "description": "desc1"}]
        })
        
        # Setup evaluation service mock for content retrieval
        mock_eval = MagicMock()
        mock_eval._get_file_content.return_value = "print('hello')"
        
        with patch.object(AegisKernel, "_get_active_context", mock_context):
            with patch.object(AegisKernel, "_evaluation_service", mock_eval):
                content = await kernel.aegis_read_file("test.py", session_id="test")
        
        # Should have Micro-Context header
        assert "# [AEGIS CONTEXT: test.py]" in content
        assert "ACTIVE LAWS: rule1" in content
        # Should NOT contain descriptions (Compression check)
        assert "desc1" not in content

    @pytest.mark.asyncio
    async def test_phase_3_4_shell_bypass_mitigation(self, kernel, tmp_path):
        """Verify that aegis_run_command detects drift and REVERTS via git."""
        # Setup git repo in tmp_path
        import subprocess
        subprocess.run(["git", "init"], cwd=tmp_path, capture_output=True)
        (tmp_path / "safe.py").write_text("safe = True")
        subprocess.run(["git", "add", "."], cwd=tmp_path, capture_output=True)
        subprocess.run(["git", "commit", "-m", "initial"], cwd=tmp_path, capture_output=True)
        
        # Use AsyncMock for coroutines
        mock_compliance = AsyncMock()
        mock_compliance.return_value = json.dumps({"passed": False})
        
        with patch.object(AegisKernel, "_validate_architecture_compliance", mock_compliance):
            # Attempt a 'bypass' command
            cmd = "echo 'leak = True' >> safe.py"
            result = await kernel.aegis_run_command(cmd)
        
        assert "ABORTED" in result
        assert "REVERTED" in result
        
        # Verify disk was reverted
        disk_content = (tmp_path / "safe.py").read_text()
        assert "leak = True" not in disk_content
        assert "safe = True" in disk_content
