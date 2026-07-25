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
VERBOSE = os.environ.get("VERBOSE", "").lower() in ("1", "true", "yes")


def debug(msg: str):
    """输出调试日志"""
    if VERBOSE:
        print(f"  🐛 {msg}")


def load_marketplace():
    """加载 marketplace.json"""
    with open(MARKETPLACE_FILE, 'r', encoding='utf-8') as f:
        return json.load(f)


def validate_schema():
    """验证 marketplace.json 格式"""
    errors = []
    debug(f"Loading marketplace.json from: {MARKETPLACE_FILE}")
    
    try:
        data = load_marketplace()
    except json.JSONDecodeError as e:
        return [f"Invalid JSON: {e}"]
    
    total_plugins = sum(1 for k in data.keys() if not k.startswith("$"))
    debug(f"Loaded marketplace.json: {total_plugins} plugins found")

    # 检查 $meta
    meta = data.get("$meta")
    if not meta:
        errors.append("Missing $meta section")
        debug("❌ Missing $meta section")
    else:
        debug(f"$meta: schema_version={meta.get('schema_version')}, name={meta.get('name')}")
        if "schema_version" not in meta:
            errors.append("Missing $meta.schema_version")
            debug("❌ Missing $meta.schema_version")
        if "name" not in meta:
            errors.append("Missing $meta.name")
            debug("❌ Missing $meta.name")

    # 检查每个插件记录
    validated = 0
    for key, value in data.items():
        if key.startswith("$"):
            continue
        
        validated += 1
        debug(f"Validating schema for: {key}")

        # plugin_id 格式检查
        if "/" not in key:
            errors.append(f"Invalid plugin_id '{key}': must be 'author/name' format")
            debug(f"  ❌ Invalid plugin_id format")
            continue

        # 必填字段
        missing_fields = []
        for field in REQUIRED_FIELDS:
            if field not in value:
                missing_fields.append(field)
                errors.append(f"[{key}] Missing required field: {field}")
        if missing_fields:
            debug(f"  ❌ Missing fields: {', '.join(missing_fields)}")
        else:
            debug(f"  ✅ All required fields present")

        # plugin_id 一致性
        expected_id = f"{value.get('author', '')}/{value.get('name', '')}"
        if expected_id != key:
            errors.append(f"[{key}] ID mismatch: expected {expected_id}")
            debug(f"  ❌ ID mismatch: key={key}, expected={expected_id}")

        # repo URL 格式（可选字段）
        repo = value.get("repo", "")
        if repo:
            debug(f"  📦 Repo: {repo}")
            if not repo.startswith("https://github.com/"):
                errors.append(f"[{key}] Repo must be GitHub URL: {repo}")
                debug(f"  ❌ Not a GitHub URL")
            else:
                # 检查仓库名是否以 tooldelta_plugin_ 开头
                # 白名单：官方插件仓库可以跳过此检查
                repo_path = repo[len("https://github.com/"):].strip("/")
                repo_name = repo_path.split("/")[-1] if "/" in repo_path else repo_path
                owner = repo_path.split("/")[0] if "/" in repo_path else ""
                
                # 官方插件仓库白名单
                is_official_repo = owner == "ToolDelta-Basic" or repo_name == "PluginMarket"
                debug(f"  👤 Owner: {owner}, Repo: {repo_name}, Official: {is_official_repo}")
                
                if not is_official_repo and not repo_name.startswith("tooldelta_plugin_"):
                    errors.append(f"[{key}] Repo name must start with 'tooldelta_plugin_': {repo_name}")
                    debug(f"  ❌ Repo name doesn't start with 'tooldelta_plugin_'")
                else:
                    debug(f"  ✅ Repo name valid")
        else:
            debug(f"  ⚠️  No repo field (skip repo validation)")

        # 检查 TooDelta 兼容字段
        if "plugin-id" in value:
            plugin_id = value.get("plugin-id")
            debug(f"  🔑 plugin-id: {plugin_id}")
            if not plugin_id:
                errors.append(f"[{key}] plugin-id cannot be empty")
                debug(f"  ❌ plugin-id is empty")

        if "plugin-type" in value:
            plugin_type = value.get("plugin-type")
            debug(f"  📋 plugin-type: {plugin_type}")
            if plugin_type not in ("classic",):
                errors.append(f"[{key}] Invalid plugin-type: {plugin_type}")
                debug(f"  ❌ Invalid plugin-type")

    debug(f"Schema validation complete: {validated} plugins validated, {len(errors)} errors")
    return errors


def validate_repos():
    """检查插件仓库可访问性"""
    errors = []
    data = load_marketplace()
    
    checked = 0
    skipped = 0

    for key, value in data.items():
        if key.startswith("$"):
            continue
        repo = value.get("repo", "")
        if not repo:
            skipped += 1
            debug(f"[{key}] ⚠️  No repo field, skipping")
            continue
        
        checked += 1
        debug(f"[{key}] Checking repo: {repo}")
        try:
            resp = requests.head(repo, timeout=10, allow_redirects=True)
            if resp.status_code >= 400:
                errors.append(f"[{key}] Repo not accessible: {repo} (HTTP {resp.status_code})")
                debug(f"  ❌ HTTP {resp.status_code}")
            else:
                debug(f"  ✅ HTTP {resp.status_code}")
        except Exception as e:
            errors.append(f"[{key}] Failed to reach repo: {repo} ({e})")
            debug(f"  ❌ Error: {e}")

    debug(f"Repo validation complete: {checked} checked, {skipped} skipped, {len(errors)} errors")
    return errors


def validate_sizes():
    """检查插件大小"""
    errors = []
    data = load_marketplace()
    
    checked = 0
    skipped = 0

    for key, value in data.items():
        if key.startswith("$"):
            continue
        repo = value.get("repo", "")
        if not repo:
            skipped += 1
            debug(f"[{key}] ⚠️  No repo field, skipping size check")
            continue

        checked += 1
        debug(f"[{key}] Checking plugin size...")
        
        # 下载 ZIP 检查大小
        zip_url_main = repo.rstrip("/") + "/archive/refs/heads/main.zip"
        zip_url_master = repo.rstrip("/") + "/archive/refs/heads/master.zip"
        
        size_found = False
        for branch, zip_url in [("main", zip_url_main), ("master", zip_url_master)]:
            try:
                debug(f"  Trying branch {branch}: {zip_url}")
                resp = requests.head(zip_url, timeout=10, allow_redirects=True)
                if resp.status_code == 200:
                    size_bytes = int(resp.headers.get('Content-Length', 0))
                    size_mb = size_bytes / (1024 * 1024)
                    debug(f"  ✅ Found on {branch}: {size_mb:.2f}MB")
                    
                    if size_mb > MAX_SIZE_MB:
                        errors.append(f"[{key}] Plugin size {size_mb:.1f}MB exceeds {MAX_SIZE_MB}MB limit")
                        debug(f"  ❌ Exceeds limit of {MAX_SIZE_MB}MB")
                    size_found = True
                    break
                else:
                    debug(f"  ⚠️  HTTP {resp.status_code} on {branch}")
            except Exception as e:
                debug(f"  ❌ Error on {branch}: {e}")
                continue
        
        if not size_found:
            debug(f"  ⚠️  Could not determine size (no branch found)")

    debug(f"Size validation complete: {checked} checked, {skipped} skipped, {len(errors)} errors")
    return errors


def validate_metadata():
    """验证远程 metadata.yaml 或 datas.json（TooDelta 兼容）"""
    errors = []
    data = load_marketplace()
    
    checked = 0
    skipped = 0
    valid = 0

    for key, value in data.items():
        if key.startswith("$"):
            continue
        repo = value.get("repo", "")
        if not repo:
            skipped += 1
            debug(f"[{key}] ⚠️  No repo field, skipping metadata validation")
            continue
        
        checked += 1
        debug(f"[{key}] Validating remote metadata...")
        debug(f"  Repo: {repo}")

        # 尝试从 raw.githubusercontent.com 获取 metadata.yaml 或 datas.json
        parsed = urlparse(repo)
        path_parts = parsed.path.strip("/").split("/")
        if len(path_parts) >= 2:
            owner, repo_name = path_parts[0], path_parts[1]
            
            # 判断仓库类型：官方插件仓库 vs 独立插件仓库
            is_official_repo = owner == "ToolDelta-Basic" or repo_name == "PluginMarket"
            
            # 获取插件目录名（优先使用 dir_name，其次使用 name）
            plugin_dir_name = value.get("dir_name", value.get("name", ""))
            debug(f"  Owner: {owner}, Repo: {repo_name}")
            debug(f"  Official repo: {is_official_repo}")
            debug(f"  Plugin dir: {plugin_dir_name}")
            
            # 先尝试 metadata.yaml，再尝试 datas.json
            found = False
            for branch in ["main", "master"]:
                if found:
                    break
                for filename in ["metadata.yaml", "datas.json"]:
                    # 根据仓库类型构建不同的路径
                    if is_official_repo and plugin_dir_name:
                        # 官方仓库：插件在子目录中
                        raw_url = f"https://raw.githubusercontent.com/{owner}/{repo_name}/{branch}/{plugin_dir_name}/{filename}"
                    else:
                        # 独立仓库：插件在根目录
                        raw_url = f"https://raw.githubusercontent.com/{owner}/{repo_name}/{branch}/{filename}"
                    
                    debug(f"  Trying {branch}/{filename}: {raw_url}")
                    try:
                        resp = requests.get(raw_url, timeout=10)
                        if resp.status_code == 200:
                            found = True
                            debug(f"  ✅ Found {filename} on branch {branch}")
                            try:
                                if filename.endswith(".yaml"):
                                    metadata = yaml.safe_load(resp.text)
                                    debug(f"  📄 Parsed as YAML")
                                else:
                                    metadata = json.loads(resp.text)
                                    debug(f"  📄 Parsed as JSON")
                                    # datas.json 格式转换
                                    if 'description' in metadata:
                                        metadata['desc'] = metadata['description']
                                    if 'plugin-id' in metadata:
                                        metadata['name'] = metadata.get('plugin-id')
                                
                                # 检查必填字段
                                missing = []
                                for field in REQUIRED_FIELDS:
                                    if field not in metadata:
                                        missing.append(field)
                                        errors.append(f"[{key}] {filename} missing field: {field}")
                                
                                if missing:
                                    debug(f"  ❌ Missing fields: {', '.join(missing)}")
                                else:
                                    debug(f"  ✅ All required fields present")
                                    valid += 1
                                    
                            except (yaml.YAMLError, json.JSONDecodeError) as e:
                                errors.append(f"[{key}] Invalid {filename}: {e}")
                                debug(f"  ❌ Parse error: {e}")
                            break
                        else:
                            debug(f"  ⚠️  HTTP {resp.status_code}")
                    except Exception as e:
                        debug(f"  ❌ Request error: {e}")
                        continue
            
            if not found:
                errors.append(f"[{key}] Neither metadata.yaml nor datas.json found in repo")
                debug(f"  ❌ Neither metadata.yaml nor datas.json found")

    debug(f"Metadata validation complete: {checked} checked, {skipped} skipped, {valid} valid, {len(errors)} errors")
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