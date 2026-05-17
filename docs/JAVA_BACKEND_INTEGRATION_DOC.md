# Manim Video API - Java 后端对接与架构详解（文档初稿）

> 适用仓库：`learnthink-video`
>
> 目标读者：Java 后端负责人、网关/平台负责人、联调工程师
>
> 基于代码版本梳理（以 `app/` 下当前实现为准）

---

## 1. 项目定位与边界

这个服务是一个 **同步 REST API**，用于把结构化视频请求转换为可交付视频：

1. 解析并规划请求
2. 生成 Manim 代码
3. 执行渲染
4. 若失败则自动进入诊断-修复-验证重试闭环
5. 成功后处理音频、音视频合成、质检
6. 可选上传 OSS，返回最终结果

### 1.1 这个服务负责什么

- 面向“视频生成引擎”的编排与执行
- 管理失败重试与修复学习（notice）
- 输出任务工件，支持问题追溯

### 1.2 这个服务不负责什么

- 任务排队/削峰（当前不是队列 worker 模式）
- 跨服务事务与业务编排（需由 Java 平台层处理）
- 权限认证网关能力（建议由上游网关或 BFF 负责）

---

## 2. 总体架构（Java 协作视角）

```text
Java Client / BFF / Scheduler
  -> HTTP (POST /v1/video/render)
  -> FastAPI (app/main.py + app/api/routes.py)
  -> RenderService (app/services/render_service.py)
  -> LangGraphRunner (app/graph/runner.py)
  -> Graph Nodes (app/graph/nodes.py)
      -> Agents (planner/codegen/diagnoser/repair/validator)
      -> Tools (manim/ffmpeg/ffprobe/oss)
      -> Storage (runtime/tasks + notices yaml)
```

### 2.1 关键分层职责

- `app/main.py`：FastAPI 初始化、日志初始化、`/health`
- `app/api/routes.py`：对外路由定义
- `app/services/render_service.py`：任务 id 生成、调用 runner、异常兜底
- `app/graph/builder.py`：图节点和路由拓扑
- `app/graph/nodes.py`：每个节点的真实业务逻辑
- `app/storage/task_repo.py`：任务状态、工件、最终结果落盘
- `app/models/contracts.py`：请求/响应契约模型

---

## 3. 对外接口契约（Java 最核心）

## 3.1 健康检查

- `GET /health`
- 用途：存活探针

## 3.2 发起渲染

- `POST /v1/video/render`
- 请求体模型：`RenderRequest`
- 响应体模型：`RenderResponse`

### 语义重点

- 该接口是 **同步阻塞**：会等待完整工作流结束才返回。
- 即使业务失败，也可能是 HTTP `200`，通过 `success=false` + `status=FAILED` 表示。
- `requestId` 为空时由服务端生成 UUID；建议 Java 端主动传入（用于幂等和追踪）。

## 3.3 查询任务

- `GET /v1/video/tasks/{task_id}`
- 响应：
  - `task`：任务状态快照（来自 `task_state.json`）
  - `result`：最终结果（来自 `final/final_result.json`，未完成可能为 `null`）

---

## 4. 核心请求链路（按当前代码真实流程）

图构建在 `app/graph/builder.py`，关键路径如下：

```text
START
  -> initialize_task
  -> plan_request
  -> resolve_assets
      ├─ failed -> finalize_failure -> END
      └─ success -> load_notices
  -> generate_code
      ├─ quality_fail & attempts<max -> repair_code -> increment_attempt -> render_code
      ├─ quality_fail & attempts>=max -> finalize_failure
      └─ pass -> render_code
  -> render_code
      ├─ success -> validate_previous_fix -> compose_audio_timeline
      └─ failed -> diagnose_errors -> validate_previous_fix -> repair_code -> increment_attempt -> render_code
  -> compose_audio_timeline
      ├─ failed -> finalize_failure
      └─ success -> mux_audio_video
  -> mux_audio_video
      ├─ failed -> finalize_failure
      └─ success -> media_qc
  -> media_qc
      ├─ failed -> finalize_failure
      └─ pass -> upload_video -> END
```

### 4.1 成功路径

- 成功渲染后并不会立刻结束，还会经历：音频合成 -> mux -> 质检 -> 上传
- 最终 `upload_video` 写入 `final_result.json` 并将任务状态置为 `COMPLETED`

### 4.2 失败路径

- 任何关键环节失败可进入 `finalize_failure`
- 渲染失败可触发多轮修复
- 有 loop guard 防止“无进展死循环修复”

---

## 5. 状态机与任务状态

状态模型定义在 `app/graph/state.py`，任务状态持久化模型在 `app/models/task.py`。

### 5.1 常见状态值

- `RECEIVED`
- `PLANNED`
- `CODE_GENERATED` / `CODE_REJECTED`
- `RENDERING`
- `RENDER_FAILED`
- `REPAIRING`
- `COMPLETED`
- `FAILED`

### 5.2 重试相关

- 图内重试计数：`attempt_no`
- 最大重试：`max_attempts = min(request.renderPolicy.maxRepairRounds, settings.max_attempts)`
- 默认全局上限来自 `MAX_ATTEMPTS`（`app/core/config.py`）

---

## 6. 数据模型重点说明（给 Java DTO 用）

以 `app/models/contracts.py` 为准。

### 6.1 请求模型 `RenderRequest`

顶层关键字段（JSON 别名）：

- `requestId`
- `projectBrief`
- `timedScenes`
- `renderPolicy`
- `outputPolicy`
- `storagePolicy`
- `audioPolicy`
- `bgmPolicy`
- `debugOptions`

### 6.2 响应模型 `RenderResponse`

- `taskId`
- `success`
- `status`
- `videoUrl`
- `ossObjectKey`
- `message`
- `attempts`
- `taskDir`

### 6.3 字段兼容性注意

- 当前模型未声明的字段默认会被忽略（例如示例请求中有额外字段）
- Java 端若误以为“多传字段可生效”会导致认知偏差，需在对接文档中明确

---

## 7. Agent 与工具链逻辑（面向排障）

## 7.1 主要 Agent

- `RequestPlanner`：规范化请求、输出 Scene IR、风险报告
- `ManimCodeExpert` + `DirectCodegenAgent`：双候选代码生成
- `CodegenSelector`：质量门控评分与候选选择
- `ErrorDiagnoser`：从日志提取结构化 issue
- `RepairAgent`：规则修复 + 可选 LLM fallback
- `FixValidator`：验证修复是否有效，触发 notice 学习

## 7.2 主要工具

- `RenderExecutor`：调用 `manim render`
- `AudioAssetResolver`：下载/缓存场景音频与 BGM
- `AudioTimelineComposer`：拼接音频、可选归一化、可选 ducking
- `AVMuxer`：视频+音频封装
- `MediaQC`：检查音频流存在与时长偏差
- `OSSUploader`：OSS 上传与 URL 组装

---

## 8. 运行产物与追溯目录

每个任务都有完整工件目录：`runtime/tasks/{task_id}`

典型结构：

```text
runtime/tasks/{task_id}/
  request.json
  normalized_request.json
  scene_ir.json
  risk_report.json
  audio_assets.json
  task_state.json
  attempts/
    01/
      generated.py
      stdout.log
      stderr.log
      render_report.json
      issues.json
      validation.json
      repair_decision.json
      audio_mix_report.json
      mux_report.json
      qc_report.json
  final/
    final_result.json
```

对 Java 联调价值：

- `taskId` 是跨服务问题定位主键
- 线上排障可从 `final_result.json` + 最近一次 `attempts/NN/*` 快速定位根因

---

## 9. 配置项与运行环境约束

配置定义在 `app/core/config.py`。

### 9.1 核心配置

- 服务：`HOST`、`PORT`、`LOG_LEVEL`
- 重试：`MAX_ATTEMPTS`
- 运行目录：`RUNTIME_ROOT`
- 执行器：`MANIM_BIN`、`FFMPEG_BIN`、`FFPROBE_BIN`
- OSS：`OSS_ENABLED`、`OSS_ENDPOINT`、`OSS_BUCKET`、AK/SK/STS 等

### 9.2 依赖约束（从仓库可见信息）

- Python >= 3.11（`pyproject.toml`）
- FastAPI / LangGraph / ffmpeg / Manim（Manim 运行依赖需环境满足）

---

## 10. Java 侧集成建议（落地动作）

## 10.1 接口调用策略

- 若网关超时较短，建议 Java 封装成“提交+轮询”模式：
  - 调 `POST /render`
  - 失败或超时后按 `taskId` 调 `GET /tasks/{task_id}`兜底

## 10.2 超时与重试

- 由于渲染链路较长，`POST /render` 需设置足够 read timeout
- Java 不建议对同一请求体盲目重放，建议依赖 `requestId` 控制幂等

## 10.3 结果判定

- 不要仅看 HTTP 状态码
- 统一判定规则：`success` + `status` + `message`

## 10.4 可观测性

- 建议透传并记录 `requestId/taskId` 到 Java 日志 MDC
- 针对 `FAILED` 建立告警并附上 `taskId`

---

## 11. 典型失败场景矩阵（文档可直接复用）

| 场景 | 表现 | 结果语义 | Java 处理建议 |
|------|------|----------|---------------|
| Manim 未安装/命令不可用 | `exit_code=127`，stderr 含 FileNotFoundError | `FAILED` | 识别为环境故障，触发运维告警 |
| 渲染超时 | `exit_code=124` | `FAILED` 或继续重试后失败 | 延长服务超时/优化请求规模 |
| 代码质量门控失败 | `CODE_REJECTED` 后进入 repair 或 fail | 可能 `FAILED` | 检查请求复杂度与规则 |
| 音频下载失败 | `resolve_assets` 失败 | `FAILED` | 检查音频 URL 可达性与权限 |
| 音视频合成失败 | `mux_failed` | `FAILED` | 检查 ffmpeg 与输入文件质量 |
| OSS 关闭 | 上传返回 `uploaded=false` | 仍可能 `COMPLETED`，`videoUrl` 可能空 | 允许“本地成功无公网 URL”语义 |

---

## 12. 当前已知风险/差异（写文档必须提示）

1. `README.md` 中流程图是简化版，未覆盖音频/mux/qc等新节点。
2. 文档中的默认端口存在差异：配置默认 `8000`，`start_dev.ps1` 默认 `8005`。
3. `task_state` 每次保存会重建模型，`createdAt` 可能被刷新，不严格等于首次创建时间。
4. `sample_request.json` 含模型未声明字段，服务会忽略这些字段。

---

## 13. 推荐给 Java 团队的 DTO 映射策略

- 请求与响应字段保持 camelCase（与 Python alias 对齐）
- 将 `status` 设计为枚举 + 兜底 `UNKNOWN`
- 对 `result` 允许 `null`（任务未完成场景）
- 关键 ID：`requestId`、`taskId` 统一作为链路追踪字段

---

## 14. 建议的后续演进（双方协作）

1. 增加 OpenAPI 固化与版本化，自动生成 Java DTO。
2. 增加异步任务接口（submit/query/cancel），降低同步超时风险。
3. 增加统一错误码（不仅依赖 message），提升 Java 端可编程处理能力。
4. 增加指标：平均时长、重试次数分布、失败类型分布。

---

## 15. 附：Java 联调最小流程（建议）

1. 先以最小请求验证 `/health` 与 `/render`。
2. 记录并回传 `requestId/taskId`。
3. 若业务失败，按 `taskId` 拉取 `/tasks/{task_id}` 并结合任务目录工件定位问题。
4. 通过失败矩阵区分“请求数据问题/环境问题/依赖问题”。

---

## 16. 代码定位索引（供写文档时快速跳转）

- 入口：`app/main.py`
- 路由：`app/api/routes.py`
- 服务：`app/services/render_service.py`
- 图 runner：`app/graph/runner.py`
- 图拓扑：`app/graph/builder.py`
- 路由决策：`app/graph/router.py`
- 节点实现：`app/graph/nodes.py`
- 状态定义：`app/graph/state.py`
- 契约模型：`app/models/contracts.py`
- 任务仓库：`app/storage/task_repo.py`
- notice 仓库：`app/storage/notice_repo.py`
- 渲染工具：`app/tools/render_executor.py`
- 音频工具：`app/tools/audio_asset_resolver.py`, `app/tools/audio_timeline_composer.py`
- 交付工具：`app/tools/av_muxer.py`, `app/tools/media_qc.py`, `app/tools/oss_uploader.py`

---

如果这份方向正确，下一版可以直接升级成：

- 面向 Java 的“接口规范版”（字段表 + 状态图 + 错误码）
- 面向研发的“内部实现版”（节点级时序 + 排障手册）

