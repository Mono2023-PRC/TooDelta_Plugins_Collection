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
import os
import json
import requests
import yaml
from urllib.parse import urlparse

MARKETPLACE_FILE = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "marketplace.json")
MAX_SIZE_MB = 16
REQUIRED_FIELDS = ["name", "author", "version", "desc"]


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

        # repo URL 格式（可选字段）
        repo = value.get("repo", "")
        if repo:
            if not repo.startswith("https://github.com/"):
                errors.append(f"[{key}] Repo must be GitHub URL: {repo}")
            else:
                # 检查仓库名是否以 tooldelta_plugin_ 开头
                # 白名单：官方插件仓库可以跳过此检查
                repo_path = repo[len("https://github.com/"):].strip("/")
                repo_name = repo_path.split("/")[-1] if "/" in repo_path else repo_path
                owner = repo_path.split("/")[0] if "/" in repo_path else ""
                
                # 官方插件仓库白名单
                is_official_repo = owner == "ToolDelta-Basic" or repo_name == "PluginMarket"
                
                if not is_official_repo and not repo_name.startswith("tooldelta_plugin_"):
                    errors.append(f"[{key}] Repo name must start with 'tooldelta_plugin_': {repo_name}")

        # 检查 TooDelta 兼容字段
        if "plugin-id" in value:
            plugin_id = value.get("plugin-id")
            if not plugin_id:
                errors.append(f"[{key}] plugin-id cannot be empty")

        if "plugin-type" in value:
            plugin_type = value.get("plugin-type")
            if plugin_type not in ("classic",):
                errors.append(f"[{key}] Invalid plugin-type: {plugin_type}")

    return errors


def validate_repos():
    """检查插件仓库可访问性"""
    errors = []
    data = load_marketplace()

    for key, value in data.items():
        if key.startswith("$"):
            continue
        repo = value.get("repo", "")
        if not repo:
            # TooDelta 插件可能没有 repo 字段，跳过检查
            continue
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
        if not repo:
            # TooDelta 插件可能没有 repo 字段，跳过检查
            continue

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
    """验证远程 metadata.yaml 或 datas.json（TooDelta 兼容）"""
    errors = []
    data = load_marketplace()

    for key, value in data.items():
        if key.startswith("$"):
            continue
        repo = value.get("repo", "")
        if not repo:
            # TooDelta 插件可能没有 repo 字段，跳过远程检查
            continue

        # 尝试从 raw.githubusercontent.com 获取 metadata.yaml 或 datas.json
        parsed = urlparse(repo)
        path_parts = parsed.path.strip("/").split("/")
        if len(path_parts) >= 2:
            owner, repo_name = path_parts[0], path_parts[1]
            
            # 判断仓库类型：官方插件仓库 vs 独立插件仓库
            is_official_repo = owner == "ToolDelta-Basic" or repo_name == "PluginMarket"
            
            # 获取插件目录名（优先使用 dir_name，其次使用 name）
            plugin_dir_name = value.get("dir_name", value.get("name", ""))
            
            # 先尝试 metadata.yaml，再尝试 datas.json
            found = False
            for branch in ["main", "master"]:
                for filename in ["metadata.yaml", "datas.json"]:
                    # 根据仓库类型构建不同的路径
                    if is_official_repo and plugin_dir_name:
                        # 官方仓库：插件在子目录中
                        raw_url = f"https://raw.githubusercontent.com/{owner}/{repo_name}/{branch}/{plugin_dir_name}/{filename}"
                    else:
                        # 独立仓库：插件在根目录
                        raw_url = f"https://raw.githubusercontent.com/{owner}/{repo_name}/{branch}/{filename}"
                    try:
                        resp = requests.get(raw_url, timeout=10)
                        if resp.status_code == 200:
                            found = True
                            try:
                                if filename.endswith(".yaml"):
                                    metadata = yaml.safe_load(resp.text)
                                else:
                                    metadata = json.loads(resp.text)
                                    # datas.json 格式转换
                                    if 'description' in metadata:
                                        metadata['desc'] = metadata['description']
                                    if 'plugin-id' in metadata:
                                        metadata['name'] = metadata.get('plugin-id')
                                
                                for field in REQUIRED_FIELDS:
                                    if field not in metadata:
                                        errors.append(f"[{key}] {filename} missing field: {field}")
                            except (yaml.YAMLError, json.JSONDecodeError) as e:
                                errors.append(f"[{key}] Invalid {filename}: {e}")
                            break
                    except Exception:
                        continue
                if found:
                    break
            
            if not found:
                errors.append(f"[{key}] Neither metadata.yaml nor datas.json found in repo")

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