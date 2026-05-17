# Manim 视频 API 服务（LangGraph 版）
一个基于 LangGraph 的多智能体视频生成 API 服务，用于将结构化请求转换为 Manim 代码、渲染视频、修复失败错误，并将最终产物上传至阿里云 OSS。
## 变更内容
本版本将编排层重构为 **LangGraph**：
- `StateGraph` 驱动工作流
- 每个 agent/工具被封装为图节点
- 路由使用条件边（conditional edges）
- 重试和失败处理在图状态（graph state）中进行建模
- 学习与通知更新作为状态转移（state transition）执行，而非临时循环
## 图流程
```text
START
  -> initialize_task
  -> plan_request
  -> load_notices
  -> generate_code
  -> render_code
      ├─ 成功 -> upload_video -> END
      └─ 失败  -> diagnose_errors
                 -> validate_previous_fix
                 -> decide_next_step
                      ├─ 重试 -> repair_code -> increment_attempt -> render_code
                      └─ 失败 -> finalize_failure -> END
```
## 快速开始

### 1. 环境准备
```bash
python -m venv .venv
# Windows: .venv\Scripts\activate
source .venv/bin/activate  
pip install -r requirements.txt
cp .env.example .env
```

### 2. 启动服务

#### ⚠️ Windows 用户请根据命令行工具选择：

**方案 A：使用推荐脚本（最稳妥）**
```powershell
# PowerShell
.\scripts\dev\start_dev.ps1
```

**方案 B：手动启动 (PowerShell)**
```powershell
python -m uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

**方案 C：手动启动 (CMD)**
```cmd
python -m uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```
*注：在 CMD 中请勿使用 `--reload-exclude "runtime/*"`，否则会因通配符展开导致报错。*

#### Linux/macOS
```bash
chmod +x scripts/deployment/start.sh
./scripts/deployment/start.sh
```

### 3. 验证
访问 [http://localhost:8000/docs](http://localhost:8000/docs) 查看 API 文档。

---

## 📂 项目结构说明

- **`app/`**: 核心业务代码（Agents, Graph, Tools）
- **`docs/`**: 完整的项目文档库
  - **[使用说明文档](docs/guides/使用说明文档.md)**: 详细的配置与故障排查指南
  - **[API 接口文档](docs/manim_video_api_interface_doc.md)**: Java/前端对接必读
  - **[DeepSeek 配置指南](docs/DEEPSEEK_THINKING_GUIDE.md)**: LLM 智能体配置说明
- **`scripts/`**: 运维与开发脚本（清理、启动、部署）
- **`prompts/`**: 智能体提示词模板
## 注意事项
- 需要 Python 3.11 及以上版本
- 渲染功能仍要求运行时环境中安装 Manim Community 版本及 FFmpeg
- 开发态热重载已排除 `runtime/*`，避免写入 `runtime/tasks` 产物时触发服务重启
- OSS 上传需要配置有效的阿里云 OSS 凭证
- 当设置 `OSS_ENABLED=false` 时，服务可以在不上传 OSS 的情况下独立运行
- LangGraph 仅用于流程编排，而渲染、文件 IO 和上传等确定性操作仍由底层确定性工具处理
