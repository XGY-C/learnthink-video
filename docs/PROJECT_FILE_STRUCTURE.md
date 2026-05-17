# 项目文件结构说明

## 📁 目录结构概览

```
learnthink-video/
├── app/                          # 核心应用代码
│   ├── agents/                   # AI 智能体（规划、代码生成、诊断、修复等）
│   ├── api/                      # API 路由
│   ├── core/                     # 核心配置和日志
│   ├── graph/                    # LangGraph 工作流
│   ├── llm/                      # LLM 客户端
│   ├── models/                   # 数据模型
│   ├── orchestrator/             # 任务编排器
│   ├── services/                 # 服务层
│   ├── storage/                  # 数据存储
│   ├── tools/                    # 工具函数
│   ├── utils/                    # 辅助函数
│   └── main.py                   # 应用入口
│
├── prompts/                      # Prompt 模板
│   ├── notices/                  # 通知相关 prompt
│   ├── shared/                   # 共享 prompt
│   └── system/                   # 系统 prompt
│
├── tests/                        # 测试代码
│
├── runtime/                      # 运行时数据（不提交到 Git）
│   ├── tasks/                    # 任务执行文件
│   └── audio_cache/              # 音频缓存
│
├── vendor-docs/                  # 第三方文档
│   └── manim/                    # Manim 文档
│
├── document/                     # 项目文档（历史方案）
│
├── .env.example                  # 环境变量模板
├── .env.deepseek.example         # DeepSeek 配置示例
├── requirements.txt              # Python 依赖
├── pyproject.toml               # 项目配置
├── Dockerfile                    # Docker 配置
│
├── README.md                     # 英文说明
├── README_CN.md                  # 中文说明
├── PROJECT_DOCUMENTATION.md      # 项目完整文档
├── QUICK_REFERENCE.md            # 快速参考
│
├── DEEPSEEK_THINKING_GUIDE.md    # DeepSeek 思考模式指南
├── DEEPSEEK_MODEL_UPDATE.md      # DeepSeek 模型更新说明
├── QUICK_REFERENCE_DEEPSEEK.md   # DeepSeek 快速参考
├── DEEPSEEK_IMPLEMENTATION_SUMMARY.md  # DeepSeek 实施总结
│
├── JAVA_BACKEND_INTEGRATION_DOC.md     # Java 后端集成文档
├── MANIM_DOC_SEARCH_TOOL.md      # Manim 文档搜索工具
├── OPEN_SOURCE_COMPONENTS_COMPETITION.md  # 开源组件竞赛
├── IMPLEMENTATION_SUMMARY.md     # 实施总结
├── manim_video_api_interface_doc.md  # API 接口文档
├── 使用说明文档.md                # 使用说明
│
├── setup_deepseek.bat            # Windows 配置脚本
├── setup_deepseek.sh             # Linux/Mac 配置脚本
├── test_deepseek_thinking.py     # DeepSeek 配置测试
│
├── start.sh                      # 启动脚本
├── start_dev.ps1                 # Windows 开发启动
├── check_console_logs.ps1        # 日志检查脚本
├── create_deployment_package.py  # 部署包创建
│
├── sample_request.json           # 示例请求
├── curl_example.sh               # curl 示例
└── demo_doc_search.py            # 文档搜索演示
```

## 📂 核心目录说明

### `app/` - 应用核心代码

| 子目录 | 说明 |
|--------|------|
| `agents/` | AI 智能体实现，包括规划器、代码专家、诊断器、修复代理等 |
| `api/` | FastAPI 路由定义 |
| `core/` | 核心配置、日志设置 |
| `graph/` | LangGraph 工作流定义（节点、路由器、状态机） |
| `llm/` | LLM 客户端实现（Mock、OpenAI 兼容） |
| `models/` | Pydantic 数据模型 |
| `services/` | 业务服务层 |
| `storage/` | 数据存储（任务仓库、通知仓库） |
| `tools/` | 工具函数（渲染执行、OSS 上传、媒体处理等） |
| `utils/` | 辅助函数（文件操作、哈希、日志工具） |

### `prompts/` - Prompt 模板

| 子目录 | 说明 |
|--------|------|
| `notices/` | 验证通过/拒绝的通知模板 |
| `shared/` | 共享的编码规则、Manim 规则、输出合约 |
| `system/` | 各智能体的系统提示词 |

### `tests/` - 测试代码

包含所有单元测试和集成测试，使用 pytest 框架。

### `runtime/` - 运行时数据（⚠️ 不提交到 Git）

| 子目录 | 说明 |
|--------|------|
| `tasks/` | 每个任务的执行文件、日志、生成的代码和视频 |
| `audio_cache/` | 音频文件缓存 |

**注意**: 此目录下的内容在 `.gitignore` 中被忽略，仅保留 `.gitkeep` 文件以维持目录结构。

### `vendor-docs/` - 第三方文档

存放 Manim 官方文档和其他第三方文档，用于文档搜索功能。

## 📄 配置文件

### 环境变量

| 文件 | 说明 | 是否提交 |
|------|------|---------|
| `.env.example` | 环境变量模板 | ✅ 是 |
| `.env.deepseek.example` | DeepSeek 配置示例 | ✅ 是 |
| `.env` | 实际环境变量（含密钥） | ❌ 否 |

### 依赖管理

| 文件 | 说明 |
|------|------|
| `requirements.txt` | Python 依赖包列表 |
| `pyproject.toml` | 项目元数据和构建配置 |

### Docker

| 文件 | 说明 |
|------|------|
| `Dockerfile` | Docker 镜像构建文件 |

## 📚 文档分类

### 核心文档

- `README.md` - 项目英文说明（主文档）
- `README_CN.md` - 项目中文说明
- `PROJECT_DOCUMENTATION.md` - 完整项目文档
- `QUICK_REFERENCE.md` - 快速参考指南

### DeepSeek 相关文档

- `DEEPSEEK_THINKING_GUIDE.md` - DeepSeek 思考模式完整指南
- `DEEPSEEK_MODEL_UPDATE.md` - DeepSeek 模型配置更新说明
- `QUICK_REFERENCE_DEEPSEEK.md` - DeepSeek 快速参考卡片
- `DEEPSEEK_IMPLEMENTATION_SUMMARY.md` - DeepSeek 集成实施总结

### API 和集成文档

- `manim_video_api_interface_doc.md` - API 接口完整文档
- `JAVA_BACKEND_INTEGRATION_DOC.md` - Java 后端集成文档
- `MANIM_DOC_SEARCH_TOOL.md` - Manim 文档搜索工具说明

### 其他文档

- `IMPLEMENTATION_SUMMARY.md` - 项目实施总结
- `OPEN_SOURCE_COMPONENTS_COMPETITION.md` - 开源组件竞赛说明
- `使用说明文档.md` - 详细使用说明

## 🛠️ 脚本工具

### 配置脚本

| 文件 | 平台 | 说明 |
|------|------|------|
| `setup_deepseek.bat` | Windows | DeepSeek 配置向导 |
| `setup_deepseek.sh` | Linux/Mac | DeepSeek 配置向导 |

### 测试脚本

| 文件 | 说明 |
|------|------|
| `test_deepseek_thinking.py` | DeepSeek 配置验证和测试 |

### 启动脚本

| 文件 | 平台 | 说明 |
|------|------|------|
| `start.sh` | Linux/Mac | 生产环境启动 |
| `start_dev.ps1` | Windows | 开发环境启动 |

### 辅助脚本

| 文件 | 说明 |
|------|------|
| `check_console_logs.ps1` | 检查控制台日志 |
| `create_deployment_package.py` | 创建部署包 |
| `demo_doc_search.py` | 文档搜索功能演示 |

### 示例文件

| 文件 | 说明 |
|------|------|
| `sample_request.json` | API 请求示例 |
| `curl_example.sh` | curl 调用示例 |

## 🧹 项目清理与维护

### 1. .gitignore 核心规则

项目已配置完善的 `.gitignore`，以下文件**不会**被提交到 Git：
- **敏感信息**: `.env`, `*.log`
- **运行时数据**: `runtime/tasks/*`, `runtime/audio_cache/*`, `*.mp4`, `*.png`
- **缓存与临时文件**: `__pycache__/`, `.pytest_cache/`, `.venv/`, `.idea/`

### 2. 定期清理脚本

为了释放磁盘空间，建议定期运行清理脚本：

```bash
# Windows
.\scripts\cleanup\cleanup_project.bat

# Linux/Mac
chmod +x scripts/cleanup/cleanup_project.sh
./scripts/cleanup/cleanup_project.sh
```

### 3. 目录结构维护

- **`.gitkeep`**: 在 `runtime/tasks/` 和 `runtime/audio_cache/` 中保留了 `.gitkeep` 文件，以确保空目录也能被 Git 追踪。
- **历史归档**: 开发过程中的实施总结、改进记录和临时方案已归档至 `docs/legacy/development-history/`。

## 🎯 最佳实践

### 1. 环境变量管理

```bash
# 首次使用时复制模板
cp .env.example .env
cp .env.deepseek.example .env

# 编辑 .env 填入实际配置
# 永远不要将 .env 提交到 Git
```

### 2. 运行时数据清理

```bash
# 定期清理运行时数据（可选）
rm -rf runtime/tasks/*/attempts/*
rm -rf runtime/audio_cache/*
```

### 3. 文档维护

- 核心文档放在根目录
- DeepSeek 相关文档统一命名前缀
- API 文档保持更新
- 历史方案放在 `document/` 目录

### 4. 代码组织

- 新功能添加到对应的 `app/` 子目录
- Prompt 模板放在 `prompts/` 目录
- 测试文件放在 `tests/` 目录，命名以 `test_` 开头

## 📊 文件大小建议

| 类型 | 建议大小 | 说明 |
|------|---------|------|
| 代码文件 | < 500 行 | 保持模块化和可维护性 |
| 文档文件 | < 50 KB | 大型文档考虑拆分 |
| 示例 JSON | < 100 KB | 避免过大的示例 |
| 日志文件 | 不提交 | 使用日志轮转 |

## 🔍 快速查找

### 查找特定功能

```bash
# 查找智能体实现
ls app/agents/

# 查找 API 路由
ls app/api/

# 查找测试
ls tests/

# 查找 Prompt 模板
ls prompts/
```

### 查找文档

```bash
# DeepSeek 相关
ls DEEPSEEK*.md

# API 文档
ls *api*.md

# 快速参考
ls QUICK*.md
```

---

**最后更新**: 2026-05-17  
**维护者**: 项目开发团队
