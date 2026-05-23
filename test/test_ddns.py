#!/usr/bin/env python3
"""DDNS IPv6 测试脚本

测试内容：
1. 配置文件加载
2. IPv6 地址获取
3. DNS 记录查询（API 调用）
4. 完整流程模拟（不实际创建/更新记录）
"""

import json
import os
import subprocess
import sys
import urllib.error
import urllib.request

# 添加项目根目录到路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Python 3.11+ 使用 tomllib，低版本使用 tomli
try:
    import tomllib
except ModuleNotFoundError:
    try:
        import tomli as tomllib
    except ModuleNotFoundError:
        print("[ERROR] 需要 Python 3.11+ 或安装 tomli 包")
        sys.exit(1)

PROJECT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CONFIG_PATH = os.path.join(PROJECT_DIR, "config", "env.toml")

PASS = "✓"
FAIL = "✗"


def test_config_load():
    """测试配置文件加载"""
    print(f"\n[测试 1] 加载配置文件: {CONFIG_PATH}")
    try:
        if not os.path.exists(CONFIG_PATH):
            print(f"  {FAIL} 配置文件不存在")
            return False
        with open(CONFIG_PATH, "rb") as f:
            config = tomllib.load(f)
        print(f"  {PASS} 配置加载成功")
        print(f"    API URL: {config['api']['base_url']}")
        print(f"    域名: {config['dns']['record_name']}")
        print(f"    检查间隔: {config['daemon']['check_interval']}s")
        return True
    except Exception as e:
        print(f"  {FAIL} 配置加载失败: {e}")
        return False


def test_ipv6_detection():
    """测试 IPv6 地址获取"""
    print("\n[测试 2] 获取本机 IPv6 地址")
    try:
        result = subprocess.run(
            ["ip", "-6", "addr", "show"],
            capture_output=True, text=True, timeout=10,
        )
        if result.returncode != 0:
            print(f"  {FAIL} ip 命令执行失败: {result.stderr.strip()}")
            return False

        lines = result.stdout.split("\n")
        found = []
        for line in lines:
            line = line.strip()
            if "scope global dynamic" in line and "mngtmpaddr" not in line:
                parts = line.split()
                for part in parts:
                    if "/" in part and ":" in part:
                        addr = part.split("/")[0]
                        found.append(addr)

        if found:
            print(f"  {PASS} 检测到 {len(found)} 个 global dynamic IPv6 地址:")
            for addr in found:
                print(f"    - {addr}")
            return True
        else:
            print(f"  {FAIL} 未找到 global dynamic IPv6 地址")
            print("  所有 IPv6 地址:")
            for line in result.stdout.split("\n"):
                if "inet6" in line:
                    print(f"    {line.strip()}")
            return False
    except Exception as e:
        print(f"  {FAIL} 获取 IPv6 异常: {e}")
        return False


def test_api_query():
    """测试 DNS 记录查询 API"""
    print("\n[测试 3] 查询 DNS 记录（API 调用）")
    try:
        with open(CONFIG_PATH, "rb") as f:
            config = tomllib.load(f)

        api_cfg = config["api"]
        dns_cfg = config["dns"]

        url = (
            f"{api_cfg['base_url']}?"
            f"m=domain_hub&endpoint=dns_records&action=list"
            f"&subdomain_id={dns_cfg['subdomain_id']}"
        )

        headers = {
            "X-API-Key": api_cfg["api_key"],
            "X-API-Secret": api_cfg["api_secret"],
        }

        req = urllib.request.Request(url, headers=headers)
        with urllib.request.urlopen(req, timeout=30) as resp:
            data = json.loads(resp.read().decode("utf-8"))

        print(f"  {PASS} API 请求成功")
        records = data.get("records", data.get("data", data)) if isinstance(data, dict) else data

        if isinstance(records, list):
            print(f"  共 {len(records)} 条 DNS 记录")
            record_prefix = dns_cfg["record_name"].split(".")[0]
            for r in records:
                rec_name = r.get("name", "")
                if (rec_name == record_prefix or rec_name == dns_cfg["record_name"]) and r.get("type") == "AAAA":
                    print(f"  {PASS} 找到目标 AAAA 记录:")
                    print(f"    ID: {r.get('id')}")
                    print(f"    Name: {r.get('name')}")
                    print(f"    Content: {r.get('content')}")
                    print(f"    TTL: {r.get('ttl')}")
                    return True

            print(f"  ⚠ 未找到 {dns_cfg['record_name']} 的 AAAA 记录（首次运行会自动创建）")
            return True
        else:
            print(f"  {FAIL} API 返回格式异常: {type(records)}")
            return False

    except urllib.error.HTTPError as e:
        print(f"  {FAIL} HTTP 错误 {e.code}: {e.reason}")
        return False
    except urllib.error.URLError as e:
        print(f"  {FAIL} 连接错误: {e.reason}")
        return False
    except Exception as e:
        print(f"  {FAIL} 异常: {e}")
        return False


def main():
    print("=" * 50)
    print("  DDNS IPv6 测试")
    print("=" * 50)

    results = []

    results.append(("配置加载", test_config_load()))
    results.append(("IPv6 检测", test_ipv6_detection()))
    results.append(("API 查询", test_api_query()))

    print("\n" + "=" * 50)
    print("  测试结果汇总")
    print("=" * 50)

    all_pass = True
    for name, result in results:
        status = PASS if result else FAIL
        print(f"  {status} {name}")
        if not result:
            all_pass = False

    if all_pass:
        print(f"\n  {PASS} 所有测试通过！")
    else:
        print(f"\n  {FAIL} 部分测试失败，请检查配置和网络")

    return 0 if all_pass else 1


if __name__ == "__main__":
    sys.exit(main())
