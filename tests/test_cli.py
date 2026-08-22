import pytest
from click.testing import CliRunner
from oin.cli import cli
from unittest.mock import patch, MagicMock

def test_cli_help():
    runner = CliRunner()
    result = runner.invoke(cli, ["--help"])
    assert result.exit_code == 0
    assert "OIN (Open Information Network) 命令行工具" in result.output

@patch("oin.cli.requests.request")
def test_cli_status(mock_request):
    m1 = MagicMock()
    m1.status_code = 200
    m1.json.return_value = {"status": "ok", "node": "test-node"}
    
    m2 = MagicMock()
    m2.status_code = 200
    m2.json.return_value = {"node_name": "test-node", "log_id": "log-1", "observer": {"observer_id": "obs-1"}}
    
    mock_request.side_effect = [m1, m2]
    
    runner = CliRunner()
    result = runner.invoke(cli, ["status", "--endpoint", "http://localhost:8000"])
    assert result.exit_code == 0
    assert "=== OIN 节点状态 ===" in result.output
    assert "ok" in result.output

@patch("oin.cli.sys.stdin.isatty", return_value=False)
@patch("oin.cli.CONFIG_FILE")
def test_cli_init_noninteractive(mock_config_file, mock_isatty, tmp_path):
    conf_file = tmp_path / "config"
    mock_config_file.exists.return_value = False
    mock_config_file.write_text = conf_file.write_text
    
    runner = CliRunner()
    result = runner.invoke(cli, ["init", "--endpoint", "http://test-endpoint:8000"])
    assert result.exit_code == 0
    assert "检测到非交互式环境" in result.output
