---
name: Plugin Submission
about: Submit a new plugin to the TooDelta Marketplace
title: "[Plugin] "
labels: ["plugin-submission"]
---

## Plugin Information

- **Plugin Name**: 
- **Author**: 
- **Version**: 
- **Repository URL**: 
- **Description**: 

## Checklist

- [ ] My plugin includes a `metadata.yaml` at the repository root
- [ ] The `metadata.yaml` contains all required fields: `name`, `author`, `version`, `repo`, `desc`
- [ ] My plugin repository is publicly accessible on GitHub
- [ ] The plugin package size is under 16MB
- [ ] I have tested the plugin locally
- [ ] The plugin does not contain malicious code

## Additional Notes

<!-- Any additional information about your plugin -->

---

## 收录流程说明

### 对于插件作者
请确保：
1. ✅ 你的仓库名以 `tooldelta_plugin_` 开头（如 `tooldelta_plugin_my-plugin`）
2. ✅ 仓库根目录包含 `datas.json` 或 `metadata.yaml`
3. ✅ 所有必填字段已正确填写
4. ✅ 插件已在本地测试通过

提交后请耐心等待管理员审核。

### 对于管理员
在评论中输入以下命令来收录插件：

```
/approve
```

系统将自动：
1. 🔍 验证插件仓库是否符合规范
2. 📝 将插件信息添加到 `marketplace.json`
3. ✅ 在 Issue 中回复收录结果
4. 🎉 自动关闭 Issue 并标记为 `approved`