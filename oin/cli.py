#!/usr/bin/env python3
import sys
import os
import json
from pathlib import Path
import click
import requests

CONFIG_DIR = Path.home() / ".oin"
CONFIG_FILE = CONFIG_DIR / "config"

LIMITATIONS_SUMMARY = """
=== OIN 已知限制摘要 ===
1. 时间戳：同一 content_hash 再次提交必须带有效 RFC 3161 凭证。首次提交仍可用 Observer 本地时间声明；仅提交一次时，伪造 captured_at 仍无法被发现。
2. 验证器异构性独立性待完全闭合：Node.js 验证器由同一执行上下文参考 Python 源码实现，待后续由独立执行者复现确认。
=========================
"""

def get_config_endpoint(override_endpoint: str | None) -> str:
    if override_endpoint:
        return override_endpoint.rstrip("/")
    if CONFIG_FILE.exists():
        try:
            data = json.loads(CONFIG_FILE.read_text())
            if "endpoint" in data:
                return data["endpoint"].rstrip("/")
        except Exception:
            pass
    return "http://127.0.0.1:8000"

def api_request(method: str, endpoint: str, path: str, **kwargs):
    url = f"{endpoint}{path}"
    try:
        response = requests.request(method, url, timeout=60, **kwargs)
        return response
    except requests.exceptions.ConnectionError as exc:
        click.echo(f"错误: 无法连接到节点后端 ({url})。请检查 endpoint 是否正确以及服务是否启动。", err=True)
        sys.exit(1)
    except requests.exceptions.Timeout as exc:
        click.echo(f"错误: 请求后端超时 ({url})。", err=True)
        sys.exit(1)
    except Exception as exc:
        click.echo(f"错误: 请求发生异常: {exc}", err=True)
        sys.exit(1)

@click.group()
def cli():
    """OIN (Open Information Network) 命令行工具"""
    pass

@cli.command()
@click.option("--endpoint", help="OIN 节点 endpoint URL")
def init(endpoint):
    """初始化 OIN 客户端配置"""
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    if CONFIG_FILE.exists() and not endpoint:
        click.echo("配置文件已存在 (~/.oin/config)，跳过初始化。")
        return

    is_interactive = sys.stdin.isatty()
    if is_interactive:
        click.echo(LIMITATIONS_SUMMARY)
        confirmed = click.confirm("是否确认以上已知限制并继续初始化？", default=True)
        if not confirmed:
            click.echo("初始化已取消。")
            sys.exit(0)
    else:
        click.echo(LIMITATIONS_SUMMARY, err=True)
        click.echo("检测到非交互式环境，自动确认已知限制。", err=True)

    if not endpoint:
        if is_interactive:
            endpoint = click.prompt("请输入 OIN 节点 Endpoint", default="http://127.0.0.1:8000")
        else:
            endpoint = "http://127.0.0.1:8000"

    config_data = {"endpoint": endpoint.rstrip("/")}
    CONFIG_FILE.write_text(json.dumps(config_data, indent=2))
    click.echo(f"初始化成功！Endpoint 已保存至 {CONFIG_FILE}")

@cli.command()
@click.argument("url")
@click.option("--endpoint", help="指定 OIN 节点 endpoint")
@click.option("--tsa-url", help="可选 RFC 3161 TSA URL；同一内容再次提交时必须提供有效第三方时间戳")
def submit(url, endpoint, tsa_url):
    """提交 URL 到 OIN 节点进行捕获、签名与发布"""
    ep = get_config_endpoint(endpoint)
    click.echo(f"正在向 {ep} 提交 URL: {url} ...")
    payload = {"url": url, "archive_format": "wacz", "resource_type": "html"}
    if tsa_url:
        payload["tsa_url"] = tsa_url
    resp = api_request("POST", ep, "/v1/captures", json=payload)
    if resp.status_code == 201:
        data = resp.json()
        manifest = data.get("manifest", {})
        object_id = manifest.get("object", {}).get("object_id")
        observation_id = manifest.get("observation_id")
        click.echo("成功提交并完成捕获发布！")
        click.echo(f"  Object ID:     {object_id}")
        click.echo(f"  Observation ID:{observation_id}")
    else:
        click.echo(f"提交失败 (HTTP {resp.status_code}): {resp.text}", err=True)
        sys.exit(1)

@cli.command()
@click.argument("identifier")
@click.option("--endpoint", help="指定 OIN 节点 endpoint")
@click.option("--verbose", is_flag=True, help="显示详细校验明细")
@click.option("--json", "json_output", is_flag=True, help="以 JSON 格式输出结果")
def verify(identifier, endpoint, verbose, json_output):
    """验证指定的 Observation ID 或 Object ID 的签名与 Merkle 证明"""
    ep = get_config_endpoint(endpoint)
    
    obs_id = identifier
    if identifier.startswith("oin:object:"):
        resp = api_request("GET", ep, f"/v1/objects/{identifier}/observations")
        if resp.status_code == 404:
            click.echo(f"错误: 对象不存在 ({identifier})", err=True)
            sys.exit(1)
        elif resp.status_code != 200:
            click.echo(f"错误: 无法获取对象 {identifier} 的观测记录 (HTTP {resp.status_code})", err=True)
            sys.exit(1)
        obs_list = resp.json()
        if not obs_list:
            click.echo(f"错误: 对象不存在 ({identifier})", err=True)
            sys.exit(1)
        obs_id = obs_list[-1]["observation_id"]
    
    resp = api_request("GET", ep, f"/v1/verify/{obs_id}")
    if resp.status_code == 404:
        click.echo(f"错误: 对象不存在或观测记录不存在 ({obs_id})", err=True)
        sys.exit(1)
    elif resp.status_code != 200:
        click.echo(f"验证请求失败 (HTTP {resp.status_code}): {resp.text}", err=True)
        sys.exit(1)
        
    result = resp.json()
    status = result.get("status")
    pass_fail = "PASS" if status == "VALID" else "FAIL"
    
    manifest_res = result.get("manifest", {})
    sig_valid = manifest_res.get("signature_valid", True)
    merkle_valid = result.get("transparency_proof_valid", True)

    obs_resp = api_request("GET", ep, f"/v1/observations/{obs_id}")
    object_id = None
    conflict_count = 0
    if obs_resp.status_code == 200:
        manifest = obs_resp.json()
        object_id = manifest.get("object", {}).get("object_id")
        if object_id:
            conf_resp = api_request("GET", ep, f"/v1/objects/{object_id}/conflicts")
            if conf_resp.status_code == 200:
                conflicts = conf_resp.json()
                conflict_count = len(conflicts)

    if json_output:
        out = {
            "identifier": identifier,
            "observation_id": obs_id,
            "status": pass_fail,
            "details": result,
            "conflict_count": conflict_count,
            "object_id": object_id
        }
        click.echo(json.dumps(out, indent=2))
        if pass_fail != "PASS":
            sys.exit(1)
        return

    click.echo(f"验证结果: {pass_fail} (Observation ID: {obs_id})")
    
    if not sig_valid:
        click.echo("签名无效")
    if not merkle_valid:
        click.echo("Merkle 证明无效")

    if verbose:
        click.echo("\n--- 验证明细 ---")
        click.echo(f"  Archive Hash Valid:     {result.get('archive_hash_valid')}")
        click.echo(f"  Raw Content Hash Valid: {result.get('raw_content_hash_valid')}")
        click.echo(f"  Raw Content Bytes Valid:{result.get('raw_content_bytes_valid')}")
        click.echo(f"  Signature Valid:        {sig_valid}")
        click.echo(f"  Manifest ID Valid:      {manifest_res.get('manifest_id_valid')}")
        click.echo(f"  Transparency Proof:     {merkle_valid}")
        timestamp = result.get("timestamp") or {}
        click.echo(f"  Timestamp Kind:         {timestamp.get('kind')}")
        click.echo(f"  Timestamp Status:       {timestamp.get('status')}")
        if timestamp.get("captured_at"):
            click.echo(f"  Observer captured_at:   {timestamp.get('captured_at')}")
        if timestamp.get("tsa_time"):
            click.echo(f"  TSA time:               {timestamp.get('tsa_time')}")
        vs = timestamp.get("captured_at_vs_tsa")
        if vs:
            click.echo(f"  captured_at vs TSA:     delta={vs.get('delta_seconds')}s close={vs.get('close')}")
        if manifest_res.get("errors"):
            click.echo(f"  Errors:                 {manifest_res.get('errors')}")

    if conflict_count > 0 and object_id:
        click.echo(f"\n该对象存在 {conflict_count} 个冲突版本，使用 oin conflicts {object_id} 查看")

    if pass_fail != "PASS":
        sys.exit(1)

@cli.command()
@click.argument("object_id")
@click.option("--endpoint", help="指定 OIN 节点 endpoint")
@click.option("--json", "json_output", is_flag=True, help="以 JSON 格式输出结果")
def conflicts(object_id, endpoint, json_output):
    """列出指定对象的所有冲突版本（按捕获时间或记录顺序稳定呈现）"""
    ep = get_config_endpoint(endpoint)
    resp = api_request("GET", ep, f"/v1/objects/{object_id}/conflicts")
    if resp.status_code == 404:
        click.echo(f"错误: 对象不存在 ({object_id})", err=True)
        sys.exit(1)
    elif resp.status_code != 200:
        click.echo(f"获取冲突失败 (HTTP {resp.status_code}): {resp.text}", err=True)
        sys.exit(1)
        
    conflict_list = resp.json()
    
    obs_resp = api_request("GET", ep, f"/v1/objects/{object_id}/observations")
    obs_map = {}
    if obs_resp.status_code == 200:
        obs_list = obs_resp.json()
        for m in obs_list:
            obs_map[m.get("observation_id")] = m

    conflict_list = sorted(conflict_list, key=lambda x: (x.get("observation_a_id", ""), x.get("observation_b_id", "")))

    if json_output:
        click.echo(json.dumps(conflict_list, indent=2))
        return

    click.echo(f"对象 {object_id} 的冲突版本列表 (共 {len(conflict_list)} 条冲突记录):")
    if not conflict_list:
        click.echo("  暂无冲突记录。")
        return

    for idx, c in enumerate(conflict_list, 1):
        obs_a_id = c.get("observation_a_id")
        obs_b_id = c.get("observation_b_id")
        obs_a = obs_map.get(obs_a_id, {})
        obs_b = obs_map.get(obs_b_id, {})
        
        click.echo(f"\n--- 冲突对 #{idx} ({c.get('classification', 'unknown movable')}) ---")
        click.echo(f"  分类: {c.get('classification')}")
        click.echo(f"  详情: {c.get('details')}")
        click.echo("  版本 A:")
        click.echo(f"    Observation ID: {obs_a_id}")
        click.echo(f"    签名者 (Observer): {obs_a.get('observer', {}).get('observer_id')}")
        click.echo(f"    捕获时间: {obs_a.get('capture', {}).get('captured_at')}")
        click.echo("  版本 B:")
        click.echo(f"    Observation ID: {obs_b_id}")
        click.echo(f"    签名者 (Observer): {obs_b.get('observer', {}).get('observer_id')}")
        click.echo(f"    捕获时间: {obs_b.get('capture', {}).get('captured_at')}")

@cli.command()
@click.option("--endpoint", help="指定 OIN 节点 endpoint")
@click.option("--json", "json_output", is_flag=True, help="以 JSON 格式输出结果")
def list(endpoint, json_output):
    """列出节点上的所有观测对象摘要"""
    ep = get_config_endpoint(endpoint)
    resp = api_request("GET", ep, "/v1/replication/ids")
    if resp.status_code != 200:
        click.echo(f"获取观测列表失败 (HTTP {resp.status_code}): {resp.text}", err=True)
        sys.exit(1)
        
    data = resp.json()
    obs_ids = data.get("observation_ids", [])
    
    summaries = []
    for obs_id in obs_ids:
        obs_resp = api_request("GET", ep, f"/v1/observations/{obs_id}")
        if obs_resp.status_code == 200:
            manifest = obs_resp.json()
            obj_id = manifest.get("object", {}).get("object_id")
            captured_at = manifest.get("capture", {}).get("captured_at")
            
            conf_count = 0
            if obj_id:
                conf_resp = api_request("GET", ep, f"/v1/objects/{obj_id}/conflicts")
                if conf_resp.status_code == 200:
                    conf_count = len(conf_resp.json())
            
            summaries.append({
                "observation_id": obs_id,
                "object_id": obj_id,
                "captured_at": captured_at,
                "canonical_url": manifest.get("object", {}).get("canonical_url"),
                "conflict_count": conf_count
            })

    if json_output:
        click.echo(json.dumps(summaries, indent=2))
        return

    click.echo(f"节点观测对象总数: {len(summaries)}")
    click.echo(f"{'OBJECT ID':<45} | {'CAPTURED AT':<25} | {'CONFLICTS':<10} | {'URL'}")
    click.echo("-" * 110)
    for s in summaries:
        obj_short = (s['object_id'] or '')[:42] + "..." if s['object_id'] and len(s['object_id']) > 45 else (s['object_id'] or '')
        conf_str = f"⚠️ {s['conflict_count']}" if s['conflict_count'] > 0 else "0"
        click.echo(f"{obj_short:<45} | {s['captured_at']:<25} | {conf_str:<10} | {s['canonical_url']}")

@cli.command()
@click.option("--endpoint", help="指定 OIN 节点 endpoint")
@click.option("--json", "json_output", is_flag=True, help="以 JSON 格式输出结果")
def status(endpoint, json_output):
    """显示当前节点信息与已知限制摘要"""
    ep = get_config_endpoint(endpoint)
    
    health_resp = api_request("GET", ep, "/healthz")
    health_data = health_resp.json() if health_resp.status_code == 200 else {"status": "unreachable"}
    
    node_resp = api_request("GET", ep, "/v1/node")
    node_data = node_resp.json() if node_resp.status_code == 200 else {}
    
    if json_output:
        out = {
            "endpoint": ep,
            "health": health_data,
            "node_info": node_data,
            "limitations": [
                "Timestamp freshness check missing (RFC 3161 roadmap)",
                "Validator independence unconfirmed (Node.js implemented from same context)"
            ]
        }
        click.echo(json.dumps(out, indent=2))
        return

    click.echo("=== OIN 节点状态 ===")
    click.echo(f"Endpoint:      {ep}")
    click.echo(f"Health Status: {health_data.get('status')}")
    click.echo(f"Node Name:     {health_data.get('node', node_data.get('node_name', 'unknown'))}")
    click.echo(f"Log ID:        {node_data.get('log_id', 'N/A')}")
    observer = node_data.get("observer", {})
    click.echo(f"Observer ID:   {observer.get('observer_id', 'N/A')}")
    click.echo(LIMITATIONS_SUMMARY)

app = cli

if __name__ == "__main__":
    cli()
