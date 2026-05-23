from typer.testing import CliRunner

from aegis.cli.main import AegisCLI


def test_install_help():
    cli = AegisCLI()
    result = CliRunner().invoke(cli.app, ["install", "--help"])
    assert result.exit_code == 0
    assert "Inject" in result.stdout


def test_run_help():
    cli = AegisCLI()
    result = CliRunner().invoke(cli.app, ["run", "--help"])
    assert result.exit_code == 0
    assert "Start" in result.stdout or "MCP" in result.stdout


def test_no_check_command():
    cli = AegisCLI()
    result = CliRunner().invoke(cli.app, ["check", "--help"])
    assert result.exit_code != 0
