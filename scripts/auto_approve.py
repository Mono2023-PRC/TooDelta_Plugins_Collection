#!/usr/bin/env python3
"""
自动收录插件脚本 - 由 GitHub Actions 触发

当项目管理者在 Issue 中评论 /approve 时，
此脚本自动验证插件并添加到 marketplace.json
"""

import os
import sys
import json
import re
import requests
from pathlib import Path
from urllib.parse import urlparse


MARKETPLACE_FILE = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    "marketplace.json"
)


def get_issue_body(issue_number: str, token: str) -> dict:
    """获取 Issue 内容"""
    repo = os.environ.get("GITHUB_REPOSITORY", "Mono2023-PRC/TooDelta_Plugins_Collection")
    api_url = f"https://api.github.com/repos/{repo}/issues/{issue_number}"
    headers = {
        "Authorization": f"token {token}",
        "Accept": "application/vnd.github.v3+json"
    }
    resp = requests.get(api_url, headers=headers, timeout=15)
    resp.raise_for_status()
    return resp.json()


def parse_plugin_info(body: str) -> dict:
    """从 Issue 内容中解析插件信息"""
    info = {}
    
    patterns = {
        "name": r"\*\*Plugin Name\*\*:\s*(.+)",
        "author": r"\*\*Author\*\*:\s*(.+)",
        "version": r"\*\*Version\*\*:\s*(.+)",
        "repo": r"\*\*Repository URL\*\*:\s*(.+)",
        "desc": r"\*\*Description\*\*:\s*(.+)",
    }
    
    for key, pattern in patterns.items():
        match = re.search(pattern, body)
        if match:
            info[key] = match.group(1).strip()
    
    return info


def validate_repo(repo_url: str) -> dict:
    """验证插件仓库并获取 datas.json / metadata.yaml"""
    parsed = urlparse(repo_url)
    path_parts = parsed.path.strip("/").split("/")
    if len(path_parts) < 2:
        raise ValueError(f"Invalid repo URL: {repo_url}")
    
    owner, repo_name = path_parts[0], path_parts[1]
    
    # 检查仓库名是否符合规范
    if not repo_name.startswith("tooldelta_plugin_"):
        # 白名单检查
        if owner != "ToolDelta-Basic" and repo_name != "PluginMarket":
            raise ValueError(
                f"Repo name must start with 'tooldelta_plugin_': {repo_name}. "
                f"Or it must be an official repo."
            )
    
    # 尝试获取 datas.json 或 metadata.yaml
    for branch in ["main", "master"]:
        for filename in ["datas.json", "metadata.yaml"]:
            raw_url = f"https://raw.githubusercontent.com/{owner}/{repo_name}/{branch}/{filename}"
            try:
                resp = requests.get(raw_url, timeout=10)
                if resp.status_code == 200:
                    if filename.endswith(".json"):
                        datas = json.loads(resp.text)
                    else:
                        import yaml
                        datas = yaml.safe_load(resp.text)
                    
                    # 规范化字段名
                    if "description" in datas and "desc" not in datas:
                        datas["desc"] = datas["description"]
                    if "plugin-id" in datas and "name" not in datas:
                        datas["name"] = datas["plugin-id"]
                    
                    return {
                        "datas": datas,
                        "filename": filename,
                        "branch": branch,
                        "raw_url": raw_url
                    }
            except Exception:
                continue
    
    raise ValueError(f"Neither datas.json nor metadata.yaml found in {repo_url}")


def add_plugin_to_marketplace(plugin_info: dict, datas: dict) -> str:
    """将插件添加到 marketplace.json"""
    with open(MARKETPLACE_FILE, "r", encoding="utf-8") as f:
        marketplace = json.load(f)
    
    author = plugin_info.get("author") or datas.get("author", "unknown")
    name = plugin_info.get("name") or datas.get("plugin-id") or datas.get("name", "unknown")
    version = plugin_info.get("version") or datas.get("version", "0.0.0")
    repo = plugin_info.get("repo", "")
    desc = plugin_info.get("desc") or datas.get("description") or datas.get("desc", "")
    
    plugin_key = f"{author}/{name}"
    
    if plugin_key in marketplace:
        # 更新已存在的插件
        marketplace[plugin_key].update({
            "author": author,
            "name": name,
            "version": version,
            "repo": repo,
            "desc": desc,
            "plugin-id": datas.get("plugin-id", name),
            "plugin-type": datas.get("plugin-type", "classic"),
        })
        is_new = False
    else:
        # 新增插件
        marketplace[plugin_key] = {
            "author": author,
            "name": name,
            "version": version,
            "repo": repo,
            "desc": desc,
            "plugin-id": datas.get("plugin-id", name),
            "plugin-type": datas.get("plugin-type", "classic"),
            "tags": []
        }
        is_new = True
    
    # 添加前置插件信息
    pre_plugins = datas.get("pre-plugins", {})
    if pre_plugins:
        marketplace[plugin_key]["pre-plugins"] = pre_plugins
    
    # 按字母顺序排序（$meta 保持在最前）
    meta = marketplace.pop("$meta")
    sorted_plugins = dict(sorted(marketplace.items()))
    new_marketplace = {"$meta": meta}
    new_marketplace.update(sorted_plugins)
    
    with open(MARKETPLACE_FILE, "w", encoding="utf-8") as f:
        json.dump(new_marketplace, f, ensure_ascii=False, indent=2)
    
    return plugin_key, is_new


def add_comment(issue_number: str, token: str, body: str):
    """在 Issue 中添加评论"""
    repo = os.environ.get("GITHUB_REPOSITORY", "Mono2023-PRC/TooDelta_Plugins_Collection")
    api_url = f"https://api.github.com/repos/{repo}/issues/{issue_number}/comments"
    headers = {
        "Authorization": f"token {token}",
        "Accept": "application/vnd.github.v3+json"
    }
    resp = requests.post(api_url, headers=headers, json={"body": body}, timeout=15)
    resp.raise_for_status()
    return resp.json()


def close_issue(issue_number: str, token: str, labels: list = None):
    """关闭 Issue 并添加标签"""
    repo = os.environ.get("GITHUB_REPOSITORY", "Mono2023-PRC/TooDelta_Plugins_Collection")
    api_url = f"https://api.github.com/repos/{repo}/issues/{issue_number}"
    headers = {
        "Authorization": f"token {token}",
        "Accept": "application/vnd.github.v3+json"
    }
    data = {"state": "closed"}
    if labels:
        data["labels"] = labels
    resp = requests.patch(api_url, headers=headers, json=data, timeout=15)
    resp.raise_for_status()
    return resp.json()


def main():
    if len(sys.argv) < 2:
        print("Usage: python auto_approve.py <issue_number>")
        sys.exit(1)
    
    issue_number = sys.argv[1]
    token = os.environ.get("GITHUB_TOKEN", "")
    
    if not token:
        print("❌ GITHUB_TOKEN not set")
        sys.exit(1)
    
    print(f"🔍 Processing issue #{issue_number}...")
    
    try:
        # 获取 Issue 内容
        issue = get_issue_body(issue_number, token)
        body = issue["body"]
        issue_title = issue.get("title", "")
        
        print(f"📋 Issue: {issue_title}")
        
        # 检查是否是插件提交
        if "plugin-submission" not in [l["name"] for l in issue.get("labels", [])]:
            print("⚠️  Not a plugin submission issue, skipping")
            return
        
        # 解析插件信息
        plugin_info = parse_plugin_info(body)
        print(f"   Plugin Name: {plugin_info.get('name', 'unknown')}")
        print(f"   Author: {plugin_info.get('author', 'unknown')}")
        print(f"   Repo: {plugin_info.get('repo', 'unknown')}")
        
        # 验证必填字段
        required_fields = ["name", "author", "version", "repo", "desc"]
        missing = [f for f in required_fields if not plugin_info.get(f)]
        if missing:
            raise ValueError(f"Missing required fields: {', '.join(missing)}")
        
        # 验证仓库并获取数据
        print("🔍 Validating plugin repository...")
        result = validate_repo(plugin_info["repo"])
        datas = result["datas"]
        print(f"   ✅ Found {result['filename']} on branch {result['branch']}")
        
        # 添加到 marketplace.json
        print("📝 Adding plugin to marketplace.json...")
        plugin_key, is_new = add_plugin_to_marketplace(plugin_info, datas)
        print(f"   {'Added' if is_new else 'Updated'}: {plugin_key}")
        
        # 添加成功评论
        if is_new:
            comment_body = f"""## ✅ 插件收录成功

插件 **{plugin_info['name']}** 已成功收录到插件市场！

| 字段 | 值 |
|------|-----|
| **插件 ID** | `{plugin_key}` |
| **版本** | v{plugin_info['version']} |
| **仓库** | {plugin_info['repo']} |

插件将在下次 GitHub Pages 部署后显示在市场中。

感谢你的贡献！🎉
"""
        else:
            comment_body = f"""## ✅ 插件更新成功

插件 **{plugin_info['name']}** 已更新到 v{plugin_info['version']}！

| 字段 | 值 |
|------|-----|
| **插件 ID** | `{plugin_key}` |
| **新版本** | v{plugin_info['version']} |
| **仓库** | {plugin_info['repo']} |

感谢你的贡献！🎉
"""
        
        add_comment(issue_number, token, comment_body)
        
        # 关闭 Issue 并添加 approved 标签
        labels = [l["name"] for l in issue.get("labels", [])]
        if "approved" not in labels:
            labels.append("approved")
        close_issue(issue_number, token, labels)
        
        print()
        print("✅ Plugin approved successfully!")
        
        # 输出供 Actions 使用的变量
        print(f"::set-output name=plugin_key::{plugin_key}")
        print(f"::set-output name=is_new::{str(is_new).lower()}")
        
    except Exception as e:
        print(f"❌ Error: {e}")
        
        # 添加失败评论
        try:
            error_body = f"""## ❌ 收录失败

**错误信息**：
```
{e}
```

请检查插件信息和仓库配置后重新提交。
"""
            add_comment(issue_number, token, error_body)
        except Exception:
            pass
        
        sys.exit(1)


if __name__ == "__main__":
    main()