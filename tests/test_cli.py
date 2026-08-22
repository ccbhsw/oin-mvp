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

@patch("oin.cli.requests.request")
def test_cli_verify_conflicts_three(mock_request):
    # 1. /v1/verify/{obs_id}
    m_verify = MagicMock(status_code=200)
    m_verify.json.return_value = {
        "status": "VALID",
        "archive_hash_valid": True,
        "raw_content_hash_valid": True,
        "raw_content_bytes_valid": True,
        "manifest": {"signature_valid": True, "manifest_id_valid": True, "errors": []},
        "transparency_proof_valid": True
    }
    # 2. /v1/observations/{obs_id}
    m_obs = MagicMock(status_code=200)
    m_obs.json.return_value = {
        "object": {"object_id": "oin:object:sha256:abc"}
    }
    # 3. /v1/objects/{object_id}/conflicts (3 conflicts)
    m_conf = MagicMock(status_code=200)
    m_conf.json.return_value = [{"classification": "temporal_variation"}, {"classification": "divergence"}, {"classification": "content_mutation"}]

    mock_request.side_effect = [m_verify, m_obs, m_conf]

    runner = CliRunner()
    result = runner.invoke(cli, ["verify", "oin:observation:sha256:123", "--endpoint", "http://localhost:8000"])
    assert result.exit_code == 0
    assert "PASS" in result.output
    assert "3 个冲突版本" in result.output or "3 个冲突版本" in result.output or "3 个冲突版本" in result.output or "3 个冲突版本" in result.output or "3 个冲突版本" in result.output or "存在 3 个冲突版本" in result.output

@patch("oin.cli.requests.request")
def test_cli_verify_conflicts_zero(mock_request):
    m_verify = MagicMock(status_code=200)
    m_verify.json.return_value = {
        "status": "VALID",
        "archive_hash_valid": True,
        "raw_content_hash_valid": True,
        "raw_content_bytes_valid": True,
        "manifest": {"signature_valid": True, "manifest_id_valid": True, "errors": []},
        "transparency_proof_valid": True
    }
    m_obs = MagicMock(status_code=200)
    m_obs.json.return_value = {
        "object": {"object_id": "oin:object:sha256:abc"}
    }
    m_conf = MagicMock(status_code=200)
    m_conf.json.return_value = []

    mock_request.side_effect = [m_verify, m_obs, m_conf]

    runner = CliRunner()
    result = runner.invoke(cli, ["verify", "oin:observation:sha256:123", "--endpoint", "http://localhost:8000"])
    assert result.exit_code == 0
    assert "PASS" in result.output
    assert "冲突版本" not in result.output

@patch("oin.cli.requests.request")
def test_cli_verify_invalid_signature(mock_request):
    m_verify = MagicMock(status_code=200)
    m_verify.json.return_value = {
        "status": "INVALID",
        "archive_hash_valid": True,
        "raw_content_hash_valid": True,
        "raw_content_bytes_valid": True,
        "manifest": {"signature_valid": False, "manifest_id_valid": True, "errors": ["signature invalid"]},
        "transparency_proof_valid": True
    }
    m_obs = MagicMock(status_code=200)
    m_obs.json.return_value = {"object": {"object_id": "oin:object:sha256:abc"}}
    m_conf = MagicMock(status_code=200)
    m_conf.json.return_value = []

    mock_request.side_effect = [m_verify, m_obs, m_conf]

    runner = CliRunner()
    result = runner.invoke(cli, ["verify", "oin:observation:sha256:123", "--endpoint", "http://localhost:8000"])
    assert result.exit_code != 0
    assert "FAIL" in result.output
    assert "签名无效" in result.output

@patch("oin.cli.requests.request")
def test_cli_verify_invalid_merkle(mock_request):
    m_verify = MagicMock(status_code=200)
    m_verify.json.return_value = {
        "status": "INVALID",
        "archive_hash_valid": True,
        "raw_content_hash_valid": True,
        "raw_content_bytes_valid": True,
        "manifest": {"signature_valid": True, "manifest_id_valid": True, "errors": []},
        "transparency_proof_valid": False
    }
    m_obs = MagicMock(status_code=200)
    m_obs.json.return_value = {"object": {"object_id": "oin:object:sha256:abc"}}
    m_conf = MagicMock(status_code=200)
    m_conf.json.return_value = []

    mock_request.side_effect = [m_verify, m_obs, m_conf]

    runner = CliRunner()
    result = runner.invoke(cli, ["verify", "oin:observation:sha256:123", "--endpoint", "http://localhost:8000"])
    assert result.exit_code != 0
    assert "FAIL" in result.output
    assert "Merkle 证明无效" in result.output

@patch("oin.cli.requests.request")
def test_cli_verify_object_not_found(mock_request):
    m_verify = MagicMock(status_code=404)
    mock_request.side_effect = [m_verify]

    runner = CliRunner()
    result = runner.invoke(cli, ["verify", "oin:observation:sha256:nonexistent", "--endpoint", "http://localhost:8000"])
    assert result.exit_code != 0
    assert "对象不存在" in result.output or "未找到" in result.output
