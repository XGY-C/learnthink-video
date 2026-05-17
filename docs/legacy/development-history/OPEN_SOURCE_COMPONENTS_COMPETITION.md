# 开源代码与组件使用情况说明（计算机设计大赛用）

项目名称：Manim Video API Service（LangGraph Edition）  
文档版本：V1.0  
编制日期：2026-04-27

---

## 目的
本说明用于向评审单位披露项目开发与运行过程中使用的开源组件与外部技术依赖，阐明用途与使用边界，便于合规审查与技术复核。

## 说明范围与依据
依据仓库当前版本的以下文件与代码实现进行整理：
- `requirements.txt`、`pyproject.toml`（依赖声明）
- `Dockerfile`（容器与系统依赖）
- 项目代码关键文件：`app/main.py`、`app/graph/builder.py`、`app/core/config.py`、`app/llm/openai_compatible.py`、`app/tools/oss_uploader.py`、`app/tools/audio_asset_resolver.py`、`app/tools/render_executor.py`、`app/storage/notice_repo.py`

---

## 核心开源组件与用途（简洁表）

| 组件 | 声明版本 | 主要用途 | 代码位置 |
|---|---:|---|---|
| fastapi | 0.115.12 | 后端 HTTP API 框架 | `app/main.py`、`app/api/` |
| uvicorn[standard] | 0.34.2 | ASGI 运行器 | `Dockerfile`、启动脚本 |
| pydantic | 2.11.3 | 数据模型与校验 | `app/core/config.py` 等 |
| pydantic-settings | 2.9.1 | 环境配置加载 | `app/core/config.py` |
| httpx | 0.28.1 | HTTP 客户端（资源下载、LLM 调用） | `app/tools/`、`app/llm/` |
| PyYAML | 6.0.2 | YAML 数据读写 | `app/storage/notice_repo.py` |
| langgraph | 0.6.7 | 多节点/状态图编排（编排层） | `app/graph/builder.py` |
| oss2 | 2.19.1 | 阿里云 OSS 上传 SDK（可选） | `app/tools/oss_uploader.py` |
| pytest | 8.3.5 | 测试框架（开发/CI） | `tests/` |

> 注：表中版本以 `requirements.txt` 为准，运行期还需满足系统工具依赖（见下文）。

---

## 系统级依赖（运行时）
这些工具非 Python 包，但为渲染/处理链路的强依赖：
- `manim`：用于动画渲染（由 `RenderExecutor` 调用 `manim render`）。
- `ffmpeg`：音视频处理、合成与转码（`audio_timeline_composer.py`、`av_muxer.py`）。
- `ffprobe`：媒体元数据探测（`ffprobe_reader.py`、`render_executor.py`）。

容器构建（`Dockerfile`）中建议安装项：`ffmpeg`、`libcairo2-dev`、`pkg-config`、`build-essential`。

---

## 外部服务与可选能力
- OpenAI 兼容 LLM（可选）：通过配置 `ENABLE_LLM_ASSIST=true` 并提供 `LLM_BASE_URL`/`LLM_API_KEY`/`LLM_MODEL` 即可启用（实现位置：`app/llm/`）。
- 阿里云 OSS（可选）：由 `OSS_ENABLED` 开关控制（实现位置：`app/tools/oss_uploader.py`）。
- 外部音频资源：按请求下载并缓存，使用 `httpx`（实现位置：`app/tools/audio_asset_resolver.py`）。

---

## 使用边界与合规声明
1. 本项目对第三方组件的使用为“依赖调用/接口调用”，未将第三方源码直接并入项目核心代码库（若存在第三方源码改写，会在附录单独标注）。
2. 组件版本通过 `requirements.txt` 固定管理，便于重现环境与追溯来源。
3. 组件许可证与义务以各组件官方仓库或发行页为准。若用于对外发布或二次分发，须按照对应许可证要求执行（例如署名、LICENSE 附带等）。

---

## 竞赛答辩复核依据（供评审核查）
- 依赖声明：`requirements.txt`、`pyproject.toml`  
- 运行环境：`Dockerfile`  
- 核心调用路径与实现：`app/main.py`、`app/graph/builder.py`、`app/tools/render_executor.py`、`app/tools/oss_uploader.py`、`app/llm/openai_compatible.py`、`app/tools/audio_asset_resolver.py`

---

## 维护与风险提示（建议）
- 建议在比赛提交版中保留 `requirements.txt` 并在 README 中注明运行时的系统依赖（`manim`、`ffmpeg`、`ffprobe` 等）。
- 若 `requirements.txt` 中存在“声明但未使用”的依赖（例如 `langchain`），建议在交付材料中解释保留理由或移除，以减少评审质疑点。 
- 发布/对外分发前请由法务或项目负责人复核第三方许可证合规性（如需，列出许可证清单）。

---

## 联系与责任人
如需进一步核验或导出完整许可证清单，请联系项目负责人或维护者并提供授权：
- 项目仓库路径：`/`（本仓库）
- 技术联系人：请在提交包中填写项目组联系人信息

---

（结束）

