# Manim Video API (LangGraph) 项目详解文档

> 项目路径：`D:\project_xgy\LearnThink Companion\learnthink-video`
>
> 文档基于代码事实编写，重点覆盖 `app/` 下当前生效实现。
>
> 更新时间：2026-04-07

---

## 1. 项目定位

`learnthink-video` 是一个“结构化视频脚本 -> Manim 代码 -> 渲染 -> 自动修复 -> 最终结果”的 API 服务。

核心目标：
- 接收结构化请求（`RenderRequest`）
- 自动生成可执行 Manim 代码
- 渲染失败时自动诊断与修复，并重试
- 成功后可选上传阿里云 OSS
- 输出任务状态与最终结果，并落盘全过程工件

核心特征：
- FastAPI 对外提供同步接口
- LangGraph 负责主流程编排
- 失败恢复采用“诊断-修复-验证-重试”闭环
- `runtime/tasks/{task_id}` 落盘完整追踪数据

---

## 2. 总体架构

```text
Client
  -> FastAPI (`app/main.py`)
     -> Router (`app/api/routes.py`)
        -> RenderService (`app/services/render_service.py`)
           -> LangGraphRunner (`app/graph/runner.py`)
              -> StateGraph (`app/graph/builder.py` + `app/graph/nodes.py`)
                 -> Agents / Tools / Storage
```

关键层职责：
- API 层：参数校验、统一响应模型、任务查询
- 服务层：组装 runner，兜底异常
- 图编排层：定义节点、边、条件路由、循环重试
- Agent 层：规划、代码生成、诊断、修复、验证
- Tool 层：Manim 执行、ffprobe 探测、OSS 上传
- Storage 层：任务状态和工件持久化

---

## 3. 目录与模块现状

### 3.1 主路径（当前生效）

- `app/main.py`：FastAPI 入口与 `/health`
- `app/api/routes.py`：`/v1/video/render`、`/v1/video/tasks/{task_id}`
- `app/services/render_service.py`：渲染服务入口
- `app/graph/`：LangGraph 状态机核心实现
- `app/agents/`：规则型 Agent
- `app/tools/`：渲染、上传、媒体探测
- `app/storage/`：任务仓库与 notice 仓库
- `app/models/`：请求、响应、issue、task 等模型
- `runtime/tasks/`：运行时工件目录

### 3.2 预留/遗留路径（当前主流程未调用）

- `app/orchestrator/scheduler.py`：旧式顺序调度器实现，保留但未接入 API 主链路
- `app/orchestrator/state_machine.py`：状态常量集合（配合旧调度器）
- `app/llm/`：LLM 客户端抽象与工厂，当前 `GraphNodes` 未直接使用

---

## 4. 请求到结果的主链路

### 4.1 API 入口

- `POST /v1/video/render`
  - 接收 `RenderRequest`
  - 调用 `RenderService.render`
  - 返回 `RenderResponse`
- `GET /v1/video/tasks/{task_id}`
  - 从 `TaskRepository` 读取 `task_state.json` 和 `final/final_result.json`

### 4.2 RenderService 行为

`RenderService.render` 做两件事：
- 生成 `task_id`（若请求未传 `requestId`）
- 调用 `LangGraphRunner.invoke` 执行图

异常处理：
- 如果图构建或执行抛 `RuntimeError`，返回失败结果（`status=FAILED`，`attempts=0`）

### 4.3 LangGraphRunner 行为

`LangGraphRunner.invoke` 输入状态：
- `task_id`
- `request_payload`（`request.model_dump(by_alias=True)`）

执行后：
- 直接读取 `final_state["final_result"]` 返回

---

## 5. LangGraph 工作流（代码级）

图定义文件：`app/graph/builder.py`

节点顺序（成功路径）：
1. `initialize_task`
2. `plan_request`
3. `load_notices`
4. `generate_code`
5. `render_code`
6. `upload_video`
7. END

失败循环路径：
1. `render_code` 失败后进入 `diagnose_errors`
2. `validate_previous_fix`
3. 路由 `route_after_validation`
4. `repair_code`
5. `increment_attempt`
6. 回到 `render_code`
7. 达到上限则 `finalize_failure`

条件路由：
- `route_after_render`（`app/graph/router.py`）
  - `success` -> `upload_video`
  - 达上限 -> `finalize_failure`
  - 否则 -> `diagnose_errors`
- `route_after_validation`
  - 达上限 -> `finalize_failure`
  - 否则 -> `repair_code`

---

## 6. Graph State 字段说明

状态定义：`app/graph/state.py` 中 `VideoGraphState`

关键字段：
- 任务标识：`task_id`、`status`、`attempt_no`、`max_attempts`、`task_dir`
- 请求/规划：`request_payload`、`normalized_request`、`scene_ir`、`risk_report`、`notices`
- 代码与问题：`current_code`、`current_issues`、`previous_issues`
- 渲染与修复：`last_render_report`、`last_repair_metadata`、`last_validation`
- 上传与结果：`upload_result`、`final_result`、`error_message`

---

## 7. 节点实现详解（`app/graph/nodes.py`）

### 7.1 `initialize_task`
- 使用 `RenderRequest(**state["request_payload"])` 反序列化
- 调用 `TaskRepository.init_task`
- `max_attempts = min(request.render_policy.max_repair_rounds, settings.max_attempts)`
- 落盘 `request.json`
- 初始化图内状态（`attempt_no=1`）

### 7.2 `plan_request`
- 调用 `RequestPlanner.run`
- 落盘：`normalized_request.json`、`scene_ir.json`、`risk_report.json`
- 更新任务状态为 `PLANNED`

### 7.3 `load_notices`
- 从 `prompts/notices/validated_notices.yaml` 读取规则

### 7.4 `generate_code`
- `ManimCodeExpert.run(scene_ir)` 生成完整 Python 脚本
- 状态更新为 `CODE_GENERATED`

### 7.5 `render_code`
- 创建 attempt 目录：`attempts/{NN}`
- 写入 `generated.py`
- 更新任务状态 `RENDERING`
- 调用 `RenderExecutor.run`，产出 `render_report.json`

### 7.6 `diagnose_errors`
- `ErrorDiagnoser.run(last_render_report)` 解析 stdout/stderr
- 落盘 `issues.json`
- 更新任务状态 `RENDER_FAILED`

### 7.7 `validate_previous_fix`
- 首轮无 `previous_issues` 时跳过验证
- 否则 `FixValidator.run(...)`
- 落盘 `validation.json`
- 若满足学习条件，写入 notice 仓库

### 7.8 `repair_code`
- `RepairAgent.run(code, issues, attempt_no)`
- 落盘 `repair_decision.json`
- 更新状态 `REPAIRING`
- 输出新代码并缓存 `previous_issues`

### 7.9 `increment_attempt`
- `attempt_no += 1`

### 7.10 `upload_video`
- 使用 `oss_path_prefix/task_id/file_base_name.mp4` 构建 object key
- 调用 `OSSUploader.upload`
- 保存 `final/final_result.json`
- 任务状态置为 `COMPLETED`

### 7.11 `finalize_failure`
- 生成统一失败结果
- 保存 `final/final_result.json`
- 任务状态置为 `FAILED`

---

## 8. Agent 机制

### 8.1 `RequestPlanner`（`app/agents/planner.py`）
- 对 `timed_scenes` 做规则检查
- 当前风险规则：
  - 场景时长 `duration_sec <= 0`
  - `animation_cues.target_refs` 指向不存在对象
- 输出：`normalizedRequest`、`sceneIR`、`riskReport`

### 8.2 `ManimCodeExpert`（`app/agents/code_expert.py`）
- 生成单文件 Manim 脚本
- 设置 `config.background_color/pixel_width/pixel_height/frame_rate`
- 内置 `safe_duration`
- 通过内容关键词选择图元（圆、矩形、三角、点）
- 按 scene 生成 `_play_scene_xx` 方法并串联执行

### 8.3 `ErrorDiagnoser`（`app/agents/diagnoser.py`）
- 基于正则匹配常见错误：
  - `SyntaxError`、`ImportError`、`ModuleNotFoundError`
  - `NameError`、`AttributeError`、`ValueError`
  - `FileNotFoundError`、`ffmpeg` 相关
- 生成 `IssueFingerprint`，ID 形式 `ISSUE_xxx_<sha1前12位>`
- 若无匹配且渲染失败，输出 `generic_render_failure`

### 8.4 `RepairAgent`（`app/agents/repair.py`）
- 按 `rootCauseLabel` 执行最小修复策略
- 典型策略：
  - `invalid_run_time`：替换 `run_time=0` 为 `safe_duration(0.2)`
  - `undefined_name`：补 `from manim import *`
  - `missing_import`：补 `from typing import Dict, List`
  - `missing_module`：不改代码，提示依赖问题

### 8.5 `FixValidator`（`app/agents/validator.py`）
- 比较 old/new issue 是否“同一问题”
- 输出 resolved/unresolved/blocked 列表
- 满足条件时给出 `candidateNotice`

---

## 9. Tools 与外部依赖

### 9.1 `RenderExecutor`（`app/tools/render_executor.py`）
- 组装命令：
  - `manim render <generated.py> <SceneClass> ...`
- 关键参数：
  - `--media_dir`、`--log_dir`
  - `-r width,height`
  - `--fps`
  - `--renderer`（`cairo` 或 `opengl`）
- 成功判定：
  - `exit_code == 0`
  - 视频存在
  - `video_size_bytes > 1024`
- 写入：`stdout.log`、`stderr.log`、`render_report.json`

### 9.2 `FFProbeReader`（`app/tools/ffprobe_reader.py`）
- `ffprobe` 可用时输出完整媒体元数据
- 不可用时返回 `available=false`

### 9.3 `OSSUploader`（`app/tools/oss_uploader.py`）
- `OSS_ENABLED=false` 时直接返回 `uploaded=false`
- 支持 AK/SK 与 STS Token 两种认证
- 可通过 `OSS_PUBLIC_BASE_URL` 覆盖拼接 URL

---

## 10. 存储与工件

### 10.1 `TaskRepository`（`app/storage/task_repo.py`）
- 目录：
  - `runtime/tasks/{task_id}/attempts`
  - `runtime/tasks/{task_id}/final`
  - `runtime/tasks/{task_id}/learning`
- 文件：
  - `task_state.json`
  - `final/final_result.json`
  - `attempts/{NN}/...`

### 10.2 `NoticeRepository`（`app/storage/notice_repo.py`）
- 文件：`prompts/notices/validated_notices.yaml`
- 能追加并累加 `verified_attempts`

### 10.3 典型任务目录

```text
runtime/tasks/{task_id}/
  request.json
  normalized_request.json
  scene_ir.json
  risk_report.json
  task_state.json
  attempts/
    01/
      generated.py
      stdout.log
      stderr.log
      render_report.json
      issues.json
      repair_decision.json
      validation.json
      media/
      logs/
  final/
    final_result.json
  learning/
```

---

## 11. 数据模型

定义见 `app/models/contracts.py`、`app/models/issues.py`、`app/models/task.py`。

### 11.1 请求模型 `RenderRequest`
- 顶层字段（别名）：
  - `requestId`
  - `projectBrief`
  - `timedScenes`
  - `renderPolicy`
  - `outputPolicy`
  - `storagePolicy`
  - `audioPolicy`
  - `bgmPolicy`
  - `debugOptions`

补充说明：
- `projectBrief.subtitleSpec` 已支持 `mixedTimelinePolicy`，可选值：`balanced`、`subtitle_first`、`action_first`。

### 11.2 响应模型 `RenderResponse`
- 关键字段：
  - `taskId`
  - `success`
  - `status`
  - `videoUrl`
  - `ossObjectKey`
  - `message`
  - `attempts`
  - `taskDir`

### 11.3 问题与修复模型
- `IssueFingerprint`
- `RepairDecision`
- `FixValidationResult`

### 11.4 任务状态模型 `TaskState`
- `taskId`、`status`、`attemptCount`、`maxAttempts`
- `latestIssueIds`、`finalVideoPath`、`finalOssUrl`

---

## 12. API 说明（以代码为准）

### 12.1 健康检查
- `GET /health`
- 返回：`{"status": "ok", "service": <APP_NAME>}`

### 12.2 发起渲染
- `POST /v1/video/render`
- 请求体：`RenderRequest`
- 返回体：`RenderResponse`

### 12.3 查询任务
- `GET /v1/video/tasks/{task_id}`
- 返回：
  - `task`（来自 `task_state.json`）
  - `result`（来自 `final_result.json`，可能为 `null`）

---

## 13. 配置项（`app/core/config.py`）

### 13.1 基础配置
- `APP_NAME` 默认 `Manim Video API Service`
- `APP_ENV` 默认 `dev`
- `HOST` 默认 `0.0.0.0`
- `PORT` 默认 `8000`
- `LOG_LEVEL` 默认 `INFO`

### 13.2 运行时
- `RUNTIME_ROOT` 默认 `runtime/tasks`
- `PROMPT_ROOT` 默认 `prompts`
- `MAX_ATTEMPTS` 默认 `6`

### 13.3 LLM 预留
- `ENABLE_LLM_ASSIST`
- `LLM_PROVIDER`
- `LLM_BASE_URL`
- `LLM_API_KEY`
- `LLM_MODEL`

### 13.4 OSS
- `OSS_ENABLED`
- `OSS_ENDPOINT`
- `OSS_BUCKET`
- `OSS_ACCESS_KEY_ID`
- `OSS_ACCESS_KEY_SECRET`
- `OSS_SECURITY_TOKEN`
- `OSS_PUBLIC_BASE_URL`
- `OSS_PATH_PREFIX`（默认 `videos`）

### 13.5 可执行程序
- `FFPROBE_BIN` 默认 `ffprobe`
- `MANIM_BIN` 默认 `manim`

---

## 14. 启动与运行

### 14.1 本地开发最小步骤（Windows PowerShell）

```powershell
Set-Location "D:\project_xgy\LearnThink Companion\learnthink-video"
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

### 14.2 快速调用示例

```powershell
curl.exe -X POST "http://127.0.0.1:8000/v1/video/render" -H "Content-Type: application/json" --data-binary "@sample_request.json"
```

---

## 15. 测试与质量现状

### 15.1 现有测试文件
- `tests/test_graph_router.py`
- `tests/test_issue_matching.py`
- `tests/test_notice_repo.py`

### 15.2 本次核对执行结果
- 命令：`python -u -m pytest -q`
- 结果：`6 passed in 0.44s`

### 15.3 当前测试覆盖重点
- 路由决策函数
- 问题匹配逻辑
- notice 追加逻辑

### 15.4 仍建议补充的测试
- `GraphNodes` 端到端节点测试（mock `RenderExecutor`）
- `RenderExecutor` 命令组装与异常路径测试
- `OSSUploader` 在禁用/缺依赖/STS 场景下的行为测试

---

## 16. 已知行为与风险

1. `upload_video` 节点无论 OSS 是否启用都会执行，`OSS_ENABLED=false` 时任务仍标记 `COMPLETED`，但 `videoUrl` 可能为 `null`。
2. `TaskState` 每次 `_save_task_state` 都新建模型，`createdAt` 可能被刷新，不完全等同“首次创建时间”。
3. `sample_request.json` 中存在模型未声明字段，Pydantic 默认会忽略，可能导致调用方误判“字段已生效”。
4. `app/orchestrator/scheduler.py` 与 LangGraph 双实现并存，维护时需要明确单一事实来源。
5. 生成代码主要依赖规则模板，对复杂 `animationCues` 的精细语义尚未完全展开。

---

## 17. 扩展建议（按优先级）

1. 统一编排入口：明确废弃旧 `orchestrator` 或完成切换文档，避免双轨维护。
2. 将同步渲染改为异步任务模式（队列 + worker），提升吞吐和稳定性。
3. 把 `app/llm/` 接入 `planner/code_expert/repair`，支持可配置 LLM 增强策略。
4. 补齐指标埋点（attempt 成功率、平均渲染时长、错误标签分布）。
5. 增加任务清理与归档策略，控制 `runtime/tasks` 体积增长。

---

## 18. 术语速查

- `Scene IR`：场景中间表示，连接“请求理解”和“代码生成”。
- `Issue Fingerprint`：结构化错误特征，用于修复、验证、学习。
- `Notice`：经验规则条目，保存在 `validated_notices.yaml`。
- `Attempt`：一次完整的“渲染+诊断+修复”循环单位。
- `Final Result`：对外返回并持久化的任务最终结果。

---

## 19. 维护建议

- 每次流程变更后，同步更新：
  - `PROJECT_DOCUMENTATION.md`
  - `manim_video_api_interface_doc.md`
  - `README.md` / `README_CN.md`
- 建议把“接口文档”和“内部架构文档”长期分离维护，减少受众混杂导致的信息噪音。
