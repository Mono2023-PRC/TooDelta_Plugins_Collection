# TooDelta Plugin Marketplace

TooDelta 插件市场注册表 - 收录各类 TooDelta 插件

## 📋 提交插件

1. 在 GitHub 上创建你的插件仓库（参考 [插件模板](https://github.com/Mono2023-PRC/TooDelta_Plugins_Collection/tree/main/plugin-sdk/template)）
2. 在仓库根目录添加 `metadata.yaml` 文件
3. 提交 Issue：[New Plugin Submission](https://github.com/Mono2023-PRC/TooDelta_Plugins_Collection/issues/new?labels=plugin-submission&template=plugin_submission.md)
4. 等待审核通过

## 📦 插件规范

### metadata.yaml 必需字段

```yaml
name: plugin_name          # 插件名称，kebab-case
author: your_name          # 作者名，GitHub username
version: "1.0.0"           # 语义化版本 (SemVer)
desc: "Plugin description" # 简短描述，160-220 字符
repo: "https://github.com/your_name/toodelta_plugin_name"  # 仓库地址
tags: ["tag1", "tag2"]     # 标签
requirements: []           # Python 依赖（可选）
config_schema: "_conf_schema.json"  # 配置面板（可选）
```

### 限制条件

- 插件 ZIP 包大小 ≤ 16MB
- 必须是 GitHub 公开仓库
- 不得包含恶意代码

## 🔧 本地开发

```bash
# 克隆仓库
git clone https://github.com/Mono2023-PRC/TooDelta_Plugins_Collection.git
cd TooDelta_Plugins_Collection

# 安装依赖
pip install pyyaml requests

# 运行校验
python scripts/validate.py all
```

## 📁 目录结构

```
.
├── marketplace.json          # 核心注册表
├── README.md
├── .github/
│   ├── workflows/
│   │   └── validate.yml      # CI 自动校验
│   └── ISSUE_TEMPLATE/
│       └── plugin_submission.md  # 提交模板
└── scripts/
    └── validate.py           # 本地校验脚本
```

## 📜 License

MIT License