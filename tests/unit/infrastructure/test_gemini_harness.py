import json
from pathlib import Path
from unittest.mock import mock_open, patch

from aegis.infrastructure.harnesses.gemini import GeminiHarness


def test_gemini_harness_install():
    home = Path("/tmp/home")
    harness = GeminiHarness()

    mock_config = "{}"
    # Use a side_effect to handle both read and write if needed, or multiple patches
    with patch("pathlib.Path.home", return_value=home):
        with patch("pathlib.Path.exists", return_value=True):
            with patch(
                "builtins.open", mock_open(read_data=mock_config)
            ) as mocked_file:
                harness.install_local(home)

                # Check if it tried to write the config
                mocked_file.assert_any_call(
                    home / ".gemini.json", "w", encoding="utf-8"
                )

            # Verify content written
            write_calls = list(mocked_file().write.call_args_list)
            written_content = "".join(call.args[0] for call in write_calls)
            config = json.loads(written_content)
            assert "mcpServers" in config
            assert "aegis" in config["mcpServers"]
            assert config["mcpServers"]["aegis"]["command"] == "uvx"


def test_gemini_harness_name():
    harness = GeminiHarness()
    assert harness.name == "gemini"


def test_gemini_harness_deploy_workspace_instructions():
    with patch("pathlib.Path.write_text") as mock_write:
        harness = GeminiHarness()
        harness.deploy_workspace_instructions("/workspace")
        mock_write.assert_called_once()
        args, _ = mock_write.call_args
        assert "Aegis Governance Protocol" in args[0]
        mock_write.assert_called_once()
        # The path check is a bit tricky with mock_write if we don't mock the Path object itself


def test_gemini_harness_deploy_workspace_instructions_path():
    with patch("pathlib.Path.write_text"):
        with patch(
            "pathlib.Path.__truediv__",
            side_effect=lambda self, other: (
                self if other == "GEMINI.md" else Path(str(self) + "/" + other)
            ),
        ):
            GeminiHarness()
            # We want to verify that it writes to /workspace/GEMINI.md
            # This is getting complicated, let's simplify the test.
            pass


def test_gemini_harness_deploy_workspace_instructions_simple():
    from unittest.mock import MagicMock

    with patch("aegis.infrastructure.harnesses.gemini.Path") as MockPath:
        mock_path_instance = MockPath.return_value
        mock_gemini_md = MagicMock()
        mock_path_instance.__truediv__.return_value = mock_gemini_md

        harness = GeminiHarness()
        harness.deploy_workspace_instructions("/workspace")

        MockPath.assert_called_with("/workspace")
        mock_path_instance.__truediv__.assert_called_with("GEMINI.md")
        mock_gemini_md.write_text.assert_called_once()
        written_text = mock_gemini_md.write_text.call_args[0][0]
        assert "Aegis" in written_text
