#!/usr/bin/env python3
"""
市场注册表校验脚本
Usage:
    python scripts/validate.py schema     # 验证 marketplace.json 格式
    python scripts/validate.py repos      # 检查仓库可访问性
    python scripts/validate.py sizes      # 检查插件大小
    python scripts/validate.py metadata   # 验证远程 metadata.yaml
    python scripts/validate.py all        # 运行所有校验
"""

import sys
import json
import requests
import yaml
from urllib.parse import urlparse

MARKETPLACE_FILE = "../marketplace.json"
MAX_SIZE_MB = 16
REQUIRED_FIELDS = ["name", "author", "version", "repo", "desc"]


def load_marketplace():
    """加载 marketplace.json"""
    with open(MARKETPLACE_FILE, 'r', encoding='utf-8') as f:
        return json.load(f)


def validate_schema():
    """验证 marketplace.json 格式"""
    errors = []
    try:
        data = load_marketplace()
    except json.JSONDecodeError as e:
        return [f"Invalid JSON: {e}"]

    # 检查 $meta
    meta = data.get("$meta")
    if not meta:
        errors.append("Missing $meta section")
    else:
        if "schema_version" not in meta:
            errors.append("Missing $meta.schema_version")
        if "name" not in meta:
            errors.append("Missing $meta.name")

    # 检查每个插件记录
    for key, value in data.items():
        if key.startswith("$"):
            continue

        # plugin_id 格式检查
        if "/" not in key:
            errors.append(f"Invalid plugin_id '{key}': must be 'author/name' format")
            continue

        # 必填字段
        for field in REQUIRED_FIELDS:
            if field not in value:
                errors.append(f"[{key}] Missing required field: {field}")

        # plugin_id 一致性
        expected_id = f"{value.get('author', '')}/{value.get('name', '')}"
        if expected_id != key:
            errors.append(f"[{key}] ID mismatch: expected {expected_id}")

        # repo URL 格式
        repo = value.get("repo", "")
        if not repo.startswith("https://github.com/"):
            errors.append(f"[{key}] Repo must be GitHub URL: {repo}")

    return errors


def validate_repos():
    """检查插件仓库可访问性"""
    errors = []
    data = load_marketplace()

    for key, value in data.items():
        if key.startswith("$"):
            continue
        repo = value.get("repo", "")
        try:
            resp = requests.head(repo, timeout=10, allow_redirects=True)
            if resp.status_code >= 400:
                errors.append(f"[{key}] Repo not accessible: {repo} (HTTP {resp.status_code})")
        except Exception as e:
            errors.append(f"[{key}] Failed to reach repo: {repo} ({e})")

    return errors


def validate_sizes():
    """检查插件大小"""
    errors = []
    data = load_marketplace()

    for key, value in data.items():
        if key.startswith("$"):
            continue
        repo = value.get("repo", "")

        # 下载 ZIP 检查大小
        zip_url = repo.rstrip("/") + "/archive/refs/heads/main.zip"
        try:
            resp = requests.head(zip_url, timeout=10, allow_redirects=True)
            if resp.status_code == 200:
                size_mb = int(resp.headers.get('Content-Length', 0)) / (1024 * 1024)
                if size_mb > MAX_SIZE_MB:
                    errors.append(f"[{key}] Plugin size {size_mb:.1f}MB exceeds {MAX_SIZE_MB}MB limit")
            else:
                # 尝试 master 分支
                zip_url = repo.rstrip("/") + "/archive/refs/heads/master.zip"
                resp = requests.head(zip_url, timeout=10, allow_redirects=True)
                if resp.status_code == 200:
                    size_mb = int(resp.headers.get('Content-Length', 0)) / (1024 * 1024)
                    if size_mb > MAX_SIZE_MB:
                        errors.append(f"[{key}] Plugin size {size_mb:.1f}MB exceeds {MAX_SIZE_MB}MB limit")
        except Exception as e:
            errors.append(f"[{key}] Failed to check plugin size: {e}")

    return errors


def validate_metadata():
    """验证远程 metadata.yaml"""
    errors = []
    data = load_marketplace()

    for key, value in data.items():
        if key.startswith("$"):
            continue
        repo = value.get("repo", "")

        # 尝试从 raw.githubusercontent.com 获取 metadata.yaml
        parsed = urlparse(repo)
        path_parts = parsed.path.strip("/").split("/")
        if len(path_parts) >= 2:
            owner, repo_name = path_parts[0], path_parts[1]
            raw_url = f"https://raw.githubusercontent.com/{owner}/{repo_name}/main/metadata.yaml"

            try:
                resp = requests.get(raw_url, timeout=10)
                if resp.status_code != 200:
                    raw_url = f"https://raw.githubusercontent.com/{owner}/{repo_name}/master/metadata.yaml"
                    resp = requests.get(raw_url, timeout=10)

                if resp.status_code == 200:
                    try:
                        metadata = yaml.safe_load(resp.text)
                        for field in REQUIRED_FIELDS:
                            if field not in metadata:
                                errors.append(f"[{key}] metadata.yaml missing field: {field}")
                    except yaml.YAMLError as e:
                        errors.append(f"[{key}] Invalid metadata.yaml: {e}")
                else:
                    errors.append(f"[{key}] metadata.yaml not found in repo")
            except Exception as e:
                errors.append(f"[{key}] Failed to fetch metadata.yaml: {e}")

    return errors


def run_all():
    """运行所有校验"""
    all_errors = []

    print("🔍 Validating marketplace.json schema...")
    errors = validate_schema()
    all_errors.extend(errors)
    print("✅ Schema valid" if not errors else f"❌ {len(errors)} errors")

    print("\n🔍 Checking plugin repo accessibility...")
    errors = validate_repos()
    all_errors.extend(errors)
    print("✅ All repos accessible" if not errors else f"❌ {len(errors)} errors")

    print("\n🔍 Checking plugin sizes...")
    errors = validate_sizes()
    all_errors.extend(errors)
    print("✅ All sizes within limit" if not errors else f"❌ {len(errors)} errors")

    print("\n🔍 Validating remote metadata.yaml...")
    errors = validate_metadata()
    all_errors.extend(errors)
    print("✅ All metadata valid" if not errors else f"❌ {len(errors)} errors")

    return all_errors


def main():
    if len(sys.argv) < 2:
        print("Usage: python validate.py [schema|repos|sizes|metadata|all]")
        sys.exit(1)

    command = sys.argv[1]

    if command == "schema":
        errors = validate_schema()
    elif command == "repos":
        errors = validate_repos()
    elif command == "sizes":
        errors = validate_sizes()
    elif command == "metadata":
        errors = validate_metadata()
    elif command == "all":
        errors = run_all()
    else:
        print(f"Unknown command: {command}")
        sys.exit(1)

    if errors:
        print("\n❌ VALIDATION FAILED:")
        for e in errors:
            print(f"  - {e}")
        sys.exit(1)
    elif command != "all":
        print("✅ Validation passed!")


if __name__ == "__main__":
    main()