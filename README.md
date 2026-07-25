# TooDelta Plugin Marketplace

TooDelta 插件市场注册表 - 收录各类 TooDelta 插件

> 去中心化插件市场，基于 GitHub 仓库 + marketplace.json 实现

## 📋 目录

- [插件提交](#-插件提交)
- [插件收录流程](#-插件收录流程)
- [插件规范](#-插件规范)
- [管理者操作](#-管理者操作)
- [本地开发](#-本地开发)
- [目录结构](#-目录结构)
- [校验说明](#-校验说明)

## 📋 插件提交

### 1. 准备插件仓库

在 GitHub 上创建你的插件仓库，仓库名**必须以 `tooldelta_plugin_` 开头**，例如：
- ✅ `tooldelta_plugin_my-plugin`
- ✅ `tooldelta_plugin_chatbot`
- ❌ `my-plugin` (不符合命名规范)

> 官方插件仓库（ToolDelta-Basic/PluginMarket）不受此限制

### 2. 添加插件数据文件

在仓库根目录添加 `datas.json` 或 `metadata.yaml` 文件。

**datas.json 示例（TooDelta 经典插件）：**
```json
{
  "plugin-id": "my-plugin",
  "version": "1.0.0",
  "author": "YourName",
  "plugin-type": "classic",
  "description": "插件描述",
  "pre-plugins": {}
}
```

**metadata.yaml 示例（标准格式）：**
```yaml
name: my-plugin
author: YourName
version: "1.0.0"
desc: "Plugin description"
repo: "https://github.com/YourName/tooldelta_plugin_my-plugin"
tags: ["tag1", "tag2"]
```

### 3. 提交 Issue

点击提交插件：[New Plugin Submission](https://github.com/Mono2023-PRC/TooDelta_Plugins_Collection/issues/new?labels=plugin-submission&template=plugin_submission.md)

填写插件信息并提交，等待管理员审核。

## � 插件收录流程

### 对于插件作者

1. ✅ 确保仓库名以 `tooldelta_plugin_` 开头
2. ✅ 仓库根目录包含 `datas.json` 或 `metadata.yaml`
3. ✅ 所有必填字段已正确填写
4. ✅ 插件已在本地测试通过
5. 📝 提交 Issue
6. ⏳ 等待管理员审核

### 对于管理员

在 Issue 评论中输入以下命令来收录插件：

```
/approve
```

系统将自动执行：
1. 🔍 验证插件仓库是否符合规范
2. 📝 将插件信息添加到 `marketplace.json`
3. ✅ 在 Issue 中回复收录结果
4. 🎉 自动关闭 Issue 并标记为 `approved`

## 📦 插件规范

### 必需字段

| 字段 | 说明 | datas.json | metadata.yaml |
|------|------|------------|---------------|
| `name` / `plugin-id` | 插件名称/ID | `plugin-id` | `name` |
| `author` | 作者名 | ✅ | ✅ |
| `version` | 版本号 | ✅ | ✅ |
| `desc` / `description` | 插件描述 | `description` | `desc` |
| `repo` | 仓库地址 | - | ✅ |

### 限制条件

- 插件 ZIP 包大小 ≤ 16MB
- 必须是 GitHub 公开仓库
- 不得包含恶意代码
- 仓库名必须以 `tooldelta_plugin_` 开头（官方仓库除外）

## 🔧 管理者操作

### 手动收录插件

```bash
# 从 Issue URL 收录
python scripts/add_plugin_from_issue.py --issue-url "https://github.com/..."

# 从仓库 URL 收录
python scripts/add_plugin_from_issue.py \
  --repo "https://github.com/user/tooldelta_plugin_name" \
  --name "插件名称" \
  --author "作者名"
```

### 运行校验

```bash
# 验证 marketplace.json 格式
python scripts/validate.py schema

# 检查仓库可访问性
python scripts/validate.py repos

# 检查插件大小
python scripts/validate.py sizes

# 验证远程 metadata/datas.json
python scripts/validate.py metadata

# 运行所有校验（启用详细日志）
VERBOSE=1 python scripts/validate.py all
```

## 🔍 校验说明

GitHub Actions 会在每次提交时自动运行以下校验：

| 校验项 | 说明 | 失败处理 |
|--------|------|---------|
| **Schema** | marketplace.json 格式和必填字段 | ❌ 阻止合并 |
| **Repos** | 插件仓库可访问性 | ⚠️ 警告 |
| **Sizes** | 插件大小限制 | ❌ 阻止合并 |
| **Metadata** | 远程 metadata/datas.json 验证 | ❌ 阻止合并 |

### Debug 模式

设置环境变量 `VERBOSE=1` 可启用详细调试日志：

```bash
VERBOSE=1 python scripts/validate.py metadata
```

输出示例：
```
🔍 Validating remote metadata.yaml...
  [机入/ai聊天] Checking https://raw.githubusercontent.com/.../ai聊天/datas.json
  [机入/ai聊天] ✅ Found datas.json on branch main
  [SuperScript/前置_MIDI播放器] Checking https://raw.githubusercontent.com/...
  [SuperScript/前置_MIDI播放器] ✅ Found datas.json on branch main
✅ All metadata valid
```

## � 本地开发

```bash
# 克隆仓库
git clone https://github.com/Mono2023-PRC/TooDelta_Plugins_Collection.git
cd TooDelta_Plugins_Collection

# 安装依赖
pip install pyyaml requests

# 运行校验
python scripts/validate.py schema
```

## 📁 目录结构

```
.
├── marketplace.json              # 核心注册表
├── README.md
├── .github/
│   ├── workflows/
│   │   ├── validate.yml          # CI 自动校验
│   │   └── plugin_approval.yml   # 自动收录工作流
│   └── ISSUE_TEMPLATE/
│       └── plugin_submission.md  # 提交模板
└── scripts/
    ├── validate.py               # 校验脚本
    └── auto_approve.py           # 自动收录脚本
```

## 🤝 贡献

欢迎提交 Issue 和 PR！

## 📜 License

MIT License
