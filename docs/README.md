# 项目文档索引

> 📚 本目录包含 learnthink-video 项目的所有文档

## 🚀 快速开始

- **[项目主 README](../README.md)** - 项目概述和快速开始指南
- **[快速参考](QUICK_REFERENCE.md)** - 常用命令和配置速查

## 📖 使用指南

### DeepSeek 集成
- **[DeepSeek 思考模式完整指南](DEEPSEEK_THINKING_GUIDE.md)** - DeepSeek 模型配置、使用方法和最佳实践
- **[DeepSeek 快速参考](QUICK_REFERENCE_DEEPSEEK.md)** - DeepSeek 配置速查卡片

### 后端集成
- **[Java 后端集成文档](JAVA_BACKEND_INTEGRATION_DOC.md)** - 与 Java 后端集成的详细说明

### 运维指南
- **[使用说明文档](guides/使用说明文档.md)** - 环境配置、启动流程与故障排查

## 🏗️ 架构文档

- **[项目完整文档](PROJECT_DOCUMENTATION.md)** - 系统架构、工作流程、技术细节
- **[实施总结](IMPLEMENTATION_SUMMARY.md)** - 项目实施过程和经验总结

## 📖 API 文档

- **[API 接口文档](manim_video_api_interface_doc.md)** - 完整的 API 接口说明和使用示例

## 🔧 运维文档

### 项目管理
- **[文件结构说明](PROJECT_FILE_STRUCTURE.md)** - 项目目录结构和文件组织
- **[项目清理指南](PROJECT_CLEANUP_SUMMARY.md)** - 如何维护和清理项目文件

## 📜 历史与开发记录

以下文档记录了项目的演进过程、实施总结及临时方案，归档于 `legacy/development-history/`：

- **[实施与改进总结](legacy/development-history/)** - 包含 P0 改进、诊断器策略、代码生成简化等记录
- **[工具实现文档](legacy/development-history/MANIM_DOC_SEARCH_TOOL.md)** - Manim 文档搜索工具的实现细节
- **[清理与重组指南](legacy/development-history/)** - 历史的项目整理提案与脚本说明
- **[初始方案](legacy/document/)** - 项目初期的设计方案

## 💡 使用建议

### 新用户
1. 先阅读 [项目主 README](../README.md)
2. 查看 [快速参考](QUICK_REFERENCE.md)
3. 根据需要查阅相应的使用指南

### 开发者
1. 阅读 [项目完整文档](PROJECT_DOCUMENTATION.md) 了解架构
2. 参考 [API 接口文档](manim_video_api_interface_doc.md) 进行开发
3. 查看 [实施总结](IMPLEMENTATION_SUMMARY.md) 了解最佳实践

### 运维人员
1. 查看 [文件结构说明](PROJECT_FILE_STRUCTURE.md) 了解项目布局
2. 定期运行 [项目清理脚本](../scripts/cleanup/)
3. 参考 [项目清理指南](PROJECT_CLEANUP_SUMMARY.md)

## 🔍 快速查找

### 我想...

**配置 DeepSeek**
→ [DeepSeek 思考模式完整指南](DEEPSEEK_THINKING_GUIDE.md)

**了解系统架构**
→ [项目完整文档](PROJECT_DOCUMENTATION.md)

**调用 API**
→ [API 接口文档](manim_video_api_interface_doc.md)

**与 Java 集成**
→ [Java 后端集成文档](JAVA_BACKEND_INTEGRATION_DOC.md)

**清理项目文件**
→ [项目清理指南](PROJECT_CLEANUP_SUMMARY.md)

**了解文件组织**
→ [文件结构说明](PROJECT_FILE_STRUCTURE.md)

## 📝 文档维护

### 添加新文档
1. 确定文档类型（指南/参考/API/架构/运维）
2. 放到对应的子目录
3. 在本索引中添加链接
4. 更新相关文档的引用

### 更新文档
- 保持文档之间的链接有效
- 更新最后修改时间
- 确保与代码实现一致

### 删除文档
- 确认没有其他文档引用
- 在 git 历史记录中保留
- 在本索引中标记为已废弃

---

**最后更新**: 2026-05-17  
**维护者**: 项目开发团队
