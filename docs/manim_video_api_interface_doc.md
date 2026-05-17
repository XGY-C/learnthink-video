# Manim Video API Service 接口文档

> 适用项目：`learnthink-video`
>
> 文档版本：v1.0
>
> 接口风格：REST / JSON

---

## 1. 项目概述

`Manim Video API Service` 是一个基于 **FastAPI + LangGraph** 的视频生成服务。
服务接收结构化请求后，执行如下流程：

1. 校验并规范化请求
2. 生成场景中间表示（Scene IR）
3. 生成 Manim Python 代码
4. 执行渲染
5. 如果渲染失败，则进入诊断、修复、验证的多轮闭环
6. 如果渲染成功，则上传视频到 OSS（可选）
7. 返回最终结果给请求方

---

## 2. 基础信息

### 2.1 Base URL

本地开发环境默认：

```text
http://127.0.0.1:8005
```

### 2.2 Content-Type

所有 POST 请求统一使用：

```http
Content-Type: application/json
```

### 2.3 返回格式

服务统一返回 JSON。

---

## 3. 接口列表

当前版本包含以下对外接口：

| 接口 | 方法 | 说明 |
|------|------|------|
| `/health` | GET | 健康检查 |
| `/v1/video/render` | POST | 发起视频生成任务并同步返回结果 |
| `/v1/video/tasks/{task_id}` | GET | 查询任务状态与最终结果 |

---

## 4. 健康检查接口

## 4.1 接口说明

用于检查服务是否已正常启动。

### 请求地址

```http
GET /health
```

### 请求示例

```bash
curl http://127.0.0.1:8005/health
```

### 响应示例

```json
{
  "status": "ok",
  "service": "Manim Video API Service"
}
```

### 字段说明

| 字段 | 类型 | 说明 |
|------|------|------|
| `status` | string | 服务状态，正常时为 `ok` |
| `service` | string | 服务名称 |

---

## 5. 视频生成接口

## 5.1 接口说明

发起一个视频生成任务。

当前实现为 **同步接口**：

- 请求进入后，服务会执行完整的 LangGraph 工作流
- 任务可能经历多轮修复与重试
- 最终返回成功或失败结果

### 请求地址

```http
POST /v1/video/render
```

---

## 5.2 请求体结构

### 顶层结构

```json
{
  "requestId": "string，可选",
  "projectBrief": {},
  "timedScenes": [],
  "renderPolicy": {},
  "outputPolicy": {},
  "storagePolicy": {},
  "audioPolicy": {},
  "bgmPolicy": {},
  "debugOptions": {}
}
```

### 字段说明

| 字段 | 类型 | 是否必填 | 说明 |
|------|------|----------|------|
| `requestId` | string | 否 | 请求唯一标识；未传时服务自动生成 |
| `projectBrief` | object | 是 | 全局项目约束 |
| `timedScenes` | array | 是 | 时间轴场景数组 |
| `renderPolicy` | object | 否 | 渲染策略 |
| `outputPolicy` | object | 否 | 输出策略 |
| `storagePolicy` | object | 否 | 存储策略 |
| `audioPolicy` | object | 否 | 音频合成策略 |
| `bgmPolicy` | object | 否 | 背景音乐策略 |
| `debugOptions` | object | 否 | 调试选项 |

---

## 5.3 `projectBrief` 说明

```json
{
  "style": "极简科技感",
  "manimVersion": "0.20.1",
  "videoSpec": {
    "aspectRatio": "16:9",
    "resolution": "1920x1080",
    "fps": 30,
    "background": "#0B1020"
  },
  "subtitleSpec": {
    "enabled": true,
    "position": "bottom",
    "maxLines": 2,
    "fontSize": 30,
    "mixedTimelinePolicy": "balanced"
  },
  "designRules": [
    "每个 scene 只表达一个主视觉意图",
    "字幕不能遮挡主视觉"
  ]
}
```

### `projectBrief` 字段说明

| 字段 | 类型 | 是否必填 | 说明 |
|------|------|----------|------|
| `style` | string | 否 | 全局视觉风格描述 |
| `manimVersion` | string | 否 | 目标 Manim 版本 |
| `videoSpec` | object | 否 | 视频规格 |
| `subtitleSpec` | object | 否 | 字幕规格 |
| `designRules` | array[string] | 否 | 设计规则列表 |

### `videoSpec` 字段说明

| 字段 | 类型 | 是否必填 | 说明 |
|------|------|----------|------|
| `aspectRatio` | string | 否 | 视频比例，如 `16:9` |
| `resolution` | string | 否 | 分辨率，如 `1920x1080` |
| `fps` | int | 否 | 帧率 |
| `background` | string | 否 | 背景色，HEX 格式 |

### `subtitleSpec` 字段说明

| 字段 | 类型 | 是否必填 | 说明 |
|------|------|----------|------|
| `enabled` | bool | 否 | 是否启用字幕 |
| `position` | string | 否 | 字幕位置，可选 `top` / `bottom` |
| `maxLines` | int | 否 | 最大字幕行数 |
| `fontSize` | int | 否 | 字体大小 |
| `mixedTimelinePolicy` | string | 否 | `mixed` 时间窗处理策略：`balanced` / `subtitle_first` / `action_first` |

---

## 5.4 `timedScenes` 说明

`timedScenes` 是核心输入，表示按时间轴组织的完整场景数组。

### 单个 scene 示例

```json
{
  "sceneId": "SC001",
  "audioUrl": null,
  "durationSec": 4.82,
  "sentences": [
    {
      "index": 1,
      "text": "很多人以为雨滴是泪滴形",
      "startSec": 0.0,
      "endSec": 1.98
    }
  ],
  "subtitleItems": [
    {
      "text": "很多人以为雨滴是泪滴形",
      "startSec": 0.0,
      "endSec": 1.98
    }
  ],
  "animationCues": [
    {
      "id": "CUE001",
      "targetRefs": ["OBJ001"],
      "action": "FadeIn",
      "timeSec": 0.0,
      "runTimeSec": 0.8,
      "intent": "开场呈现主体"
    }
  ],
  "sceneSpec": {
    "layoutTemplate": "center_focus",
    "objects": [
      {
        "id": "OBJ001",
        "type": "shape",
        "content": "泪滴形图标",
        "role": "错误示意",
        "placement": "center",
        "style": {
          "scale": 1.0,
          "emphasis": "high"
        }
      }
    ]
  }
}
```

### `timedScenes[]` 字段说明

| 字段 | 类型 | 是否必填 | 说明 |
|------|------|----------|------|
| `sceneId` | string | 是 | 场景唯一 ID |
| `audioUrl` | string/null | 否 | 场景配套音频地址 |
| `durationSec` | float | 是 | 场景总时长（秒） |
| `sentences` | array | 否 | 文本句子时间轴 |
| `subtitleItems` | array | 否 | 字幕时间轴 |
| `animationCues` | array | 否 | 动画线索 |
| `sceneSpec` | object | 否 | 场景布局与对象定义 |

### `sentences[]` 字段说明

| 字段 | 类型 | 是否必填 | 说明 |
|------|------|----------|------|
| `index` | int | 是 | 句子序号 |
| `text` | string | 是 | 句子文本 |
| `startSec` | float | 是 | 开始时间 |
| `endSec` | float | 是 | 结束时间 |

### `subtitleItems[]` 字段说明

| 字段 | 类型 | 是否必填 | 说明 |
|------|------|----------|------|
| `text` | string | 是 | 字幕文本 |
| `startSec` | float | 是 | 开始时间 |
| `endSec` | float | 是 | 结束时间 |

### `animationCues[]` 字段说明

| 字段 | 类型 | 是否必填 | 说明 |
|------|------|----------|------|
| `id` | string | 是 | Cue ID |
| `targetRefs` | array[string] | 否 | 作用目标对象 ID 列表 |
| `action` | string | 是 | 动画动作，例如 `FadeIn` |
| `timeSec` | float | 是 | 发生时间 |
| `runTimeSec` | float | 是 | 动画时长 |
| `intent` | string | 否 | 动画意图说明 |

### `sceneSpec` 字段说明

| 字段 | 类型 | 是否必填 | 说明 |
|------|------|----------|------|
| `layoutTemplate` | string | 否 | 布局模板 |
| `objects` | array | 否 | 场景对象定义 |

### `objects[]` 字段说明

| 字段 | 类型 | 是否必填 | 说明 |
|------|------|----------|------|
| `id` | string | 是 | 对象 ID |
| `type` | string | 是 | 对象类型 |
| `content` | string | 是 | 对象内容 |
| `role` | string | 否 | 对象语义角色 |
| `placement` | string | 否 | 摆放位置 |
| `style` | object | 否 | 样式配置 |

### `style` 字段说明

| 字段 | 类型 | 是否必填 | 说明 |
|------|------|----------|------|
| `scale` | float | 否 | 缩放比例 |
| `emphasis` | string | 否 | 强调级别 |

---

## 5.5 `renderPolicy` 说明

```json
{
  "maxRepairRounds": 3,
  "timeoutSec": 300,
  "renderer": "cairo"
}
```

| 字段 | 类型 | 是否必填 | 说明 |
|------|------|----------|------|
| `maxRepairRounds` | int | 否 | 最大修复重试轮数 |
| `timeoutSec` | int | 否 | 单次渲染超时时间（秒） |
| `renderer` | string | 否 | 渲染器，支持 `cairo` / `opengl` |

---

## 5.6 `outputPolicy` 说明

```json
{
  "sceneClassName": "GeneratedVideoScene",
  "fileBaseName": "generated_video",
  "needPoster": false
}
```

| 字段 | 类型 | 是否必填 | 说明 |
|------|------|----------|------|
| `sceneClassName` | string | 否 | Manim Scene 类名 |
| `fileBaseName` | string | 否 | 输出文件基础名 |
| `needPoster` | bool | 否 | 是否需要封面图 |

---

## 5.7 `storagePolicy` 说明

```json
{
  "provider": "aliyun_oss",
  "bucket": null,
  "region": null,
  "pathPrefix": "videos/demo"
}
```

| 字段 | 类型 | 是否必填 | 说明 |
|------|------|----------|------|
| `provider` | string | 否 | 存储提供商，当前固定为 `aliyun_oss` |
| `bucket` | string/null | 否 | 目标 bucket |
| `region` | string/null | 否 | 区域 |
| `pathPrefix` | string/null | 否 | OSS 对象前缀路径 |

---


## 5.8 `audioPolicy` 说明

```json
{
  "mode": "scene_audio",
  "normalizeVolume": false,
  "insertSilenceBetweenScenesMs": 0,
  "targetSampleRate": 44100
}
```

| 字段 | 类型 | 是否必填 | 说明 |
|------|------|----------|------|
| `mode` | string | 否 | 当前固定 `scene_audio` |
| `normalizeVolume` | bool | 否 | 是否启用整体音量归一化 |
| `insertSilenceBetweenScenesMs` | int | 否 | 场景间插入静音时长（毫秒） |
| `targetSampleRate` | int | 否 | 输出音频采样率，默认 44100 |

---

## 5.9 `bgmPolicy` 说明

```json
{
  "enabled": false,
  "url": null,
  "volume": 0.15,
  "ducking": true
}
```

| 字段 | 类型 | 是否必填 | 说明 |
|------|------|----------|------|
| `enabled` | bool | 否 | 是否启用 BGM 混音 |
| `url` | string/null | 否 | BGM 文件地址 |
| `volume` | float | 否 | BGM 音量系数 |
| `ducking` | bool | 否 | 是否对旁白主轨启用 sidechain ducking |

---

## 5.10 `debugOptions` 说明

```json
{
  "saveAttempts": true,
  "saveLogs": true,
  "savePatchedCode": true
}
```

| 字段 | 类型 | 是否必填 | 说明 |
|------|------|----------|------|
| `saveAttempts` | bool | 否 | 是否保存每轮 attempt |
| `saveLogs` | bool | 否 | 是否保存日志 |
| `savePatchedCode` | bool | 否 | 是否保存修复后的代码 |

---

## 5.11 完整请求示例

```json
{
  "requestId": "demo-task-001",
  "projectBrief": {
    "style": "极简科技感",
    "manimVersion": "0.20.1",
    "videoSpec": {
      "aspectRatio": "16:9",
      "resolution": "1920x1080",
      "fps": 30,
      "background": "#0B1020"
    },
    "subtitleSpec": {
      "enabled": true,
      "position": "bottom",
      "maxLines": 2,
      "fontSize": 30,
      "mixedTimelinePolicy": "balanced"
    },
    "designRules": [
      "每个 scene 只表达一个主视觉意图",
      "字幕不能遮挡主视觉"
    ]
  },
  "timedScenes": [
    {
      "sceneId": "SC001",
      "audioUrl": null,
      "durationSec": 4.82,
      "sentences": [
        {
          "index": 1,
          "text": "很多人以为雨滴是泪滴形",
          "startSec": 0.0,
          "endSec": 1.98
        }
      ],
      "subtitleItems": [
        {
          "text": "很多人以为雨滴是泪滴形",
          "startSec": 0.0,
          "endSec": 1.98
        }
      ],
      "animationCues": [
        {
          "id": "CUE001",
          "targetRefs": ["OBJ001"],
          "action": "FadeIn",
          "timeSec": 0.0,
          "runTimeSec": 0.8,
          "intent": "开场呈现主体"
        }
      ],
      "sceneSpec": {
        "layoutTemplate": "center_focus",
        "objects": [
          {
            "id": "OBJ001",
            "type": "shape",
            "content": "泪滴形图标",
            "role": "错误示意",
            "placement": "center",
            "style": {
              "scale": 1.0,
              "emphasis": "high"
            }
          }
        ]
      }
    }
  ],
  "renderPolicy": {
    "maxRepairRounds": 3,
    "timeoutSec": 300,
    "renderer": "cairo"
  },
  "outputPolicy": {
    "sceneClassName": "GeneratedVideoScene",
    "fileBaseName": "generated_video",
    "needPoster": false
  },
  "storagePolicy": {
    "provider": "aliyun_oss",
    "bucket": null,
    "region": null,
    "pathPrefix": "videos/demo"
  },
  "audioPolicy": {
    "mode": "scene_audio",
    "normalizeVolume": false,
    "insertSilenceBetweenScenesMs": 0,
    "targetSampleRate": 44100
  },
  "bgmPolicy": {
    "enabled": false,
    "url": null,
    "volume": 0.15,
    "ducking": true
  },
  "debugOptions": {
    "saveAttempts": true,
    "saveLogs": true,
    "savePatchedCode": true
  }
}
```

---

## 5.12 成功响应结构

```json
{
  "taskId": "demo-task-001",
  "success": true,
  "status": "COMPLETED",
  "videoUrl": "https://example.com/generated_video.mp4",
  "ossObjectKey": "videos/demo-task-001/generated_video.mp4",
  "message": "Video rendered successfully",
  "attempts": 2,
  "taskDir": "runtime/tasks/demo-task-001"
}
```

### 字段说明

| 字段 | 类型 | 说明 |
|------|------|------|
| `taskId` | string | 任务 ID |
| `success` | bool | 是否成功 |
| `status` | string | 最终状态，成功时为 `COMPLETED` |
| `videoUrl` | string/null | 视频访问地址 |
| `ossObjectKey` | string/null | OSS 对象 key |
| `message` | string | 结果描述 |
| `attempts` | int | 实际尝试次数 |
| `taskDir` | string/null | 任务归档目录 |

---

## 5.13 失败响应结构

```json
{
  "taskId": "demo-task-001",
  "success": false,
  "status": "FAILED",
  "videoUrl": null,
  "ossObjectKey": null,
  "message": "Render failed after max attempts",
  "attempts": 3,
  "taskDir": "runtime/tasks/demo-task-001"
}
```

### 常见失败原因

| 场景 | 说明 |
|------|------|
| LangGraph 未安装 | 服务未正确安装依赖 |
| Manim 未安装 | 无法执行渲染命令 |
| FFmpeg / ffprobe 未安装 | 无法探测视频信息或渲染失败 |
| 代码生成不合法 | 多轮修复后仍失败 |
| OSS 配置无效 | 渲染成功但上传失败 |

---

## 6. 查询任务接口

## 6.1 接口说明

根据 `task_id` 查询任务状态和最终结果。

### 请求地址

```http
GET /v1/video/tasks/{task_id}
```

### 路径参数

| 参数 | 类型 | 是否必填 | 说明 |
|------|------|----------|------|
| `task_id` | string | 是 | 任务 ID |

### 请求示例

```bash
curl http://127.0.0.1:8005/v1/video/tasks/demo-task-001
```

### 成功响应示例

```json
{
  "task": {
    "taskId": "demo-task-001",
    "status": "FAILED",
    "createdAt": "2026-04-06T00:00:00+00:00",
    "updatedAt": "2026-04-06T00:00:10+00:00",
    "attemptCount": 3,
    "maxAttempts": 3,
    "latestIssueIds": [
      "ISSUE_001_xxx"
    ],
    "finalVideoPath": null,
    "finalOssUrl": null
  },
  "result": {
    "taskId": "demo-task-001",
    "success": false,
    "status": "FAILED",
    "videoUrl": null,
    "ossObjectKey": null,
    "message": "Render failed after max attempts",
    "attempts": 3,
    "taskDir": "runtime/tasks/demo-task-001"
  }
}
```

### 字段说明

#### `task`

| 字段 | 类型 | 说明 |
|------|------|------|
| `taskId` | string | 任务 ID |
| `status` | string | 当前任务状态 |
| `createdAt` | string | 创建时间 |
| `updatedAt` | string | 更新时间 |
| `attemptCount` | int | 当前尝试次数 |
| `maxAttempts` | int | 最大尝试次数 |
| `latestIssueIds` | array[string] | 最近一次 issue 列表 |
| `finalVideoPath` | string/null | 本地最终视频路径 |
| `finalOssUrl` | string/null | 最终 OSS 链接 |

#### `result`

最终结果对象，与 `/v1/video/render` 的响应格式一致。

---

## 7. 任务状态说明

系统内部常见状态如下：

| 状态 | 说明 |
|------|------|
| `RECEIVED` | 已接收请求 |
| `PLANNED` | 已完成请求规范化与规划 |
| `CODE_GENERATED` | 已生成初始 Manim 代码 |
| `RENDERING` | 正在渲染 |
| `RENDER_FAILED` | 当前轮渲染失败 |
| `REPAIRING` | 正在修复代码 |
| `COMPLETED` | 成功完成 |
| `FAILED` | 超过重试上限或环境异常 |

---

## 8. 调用示例

## 8.1 使用 curl 生成视频

```bash
curl -X POST http://127.0.0.1:8005/v1/video/render \
  -H "Content-Type: application/json" \
  -d @sample_request.json
```

## 8.2 使用 Python 调用

```python
import requests
import json

with open("sample_request.json", "r", encoding="utf-8") as f:
    payload = json.load(f)

resp = requests.post(
    "http://127.0.0.1:8005/v1/video/render",
    json=payload,
    timeout=600,
)

print(resp.status_code)
print(resp.json())
```

---

## 9. 错误码说明

当前项目主要依赖 HTTP 标准状态码。

| 状态码 | 说明 |
|--------|------|
| `200` | 请求成功，接口正常返回结果 |
| `404` | 指定任务不存在 |
| `422` | 请求参数校验失败 |
| `500` | 服务内部异常 |

### `422` 常见原因

- 缺少必填字段
- 字段类型错误
- JSON 结构不符合 Pydantic 模型定义

---

## 10. 运行产物目录说明

每个任务会在 `runtime/tasks/{task_id}` 下保存归档产物。

### 典型目录结构

```text
runtime/tasks/{task_id}/
├── request.json
├── normalized_request.json
├── scene_ir.json
├── risk_report.json
├── task_state.json
├── attempts/
│   ├── 01/
│   │   ├── generated.py
│   │   ├── stdout.log
│   │   ├── stderr.log
│   │   ├── render_report.json
│   │   ├── issues.json
│   │   ├── repair_decision.json
│   │   └── validation.json
│   └── 02/
└── final/
    └── final_result.json
```

### 主要文件说明

| 文件 | 说明 |
|------|------|
| `request.json` | 原始请求 |
| `normalized_request.json` | 规范化请求 |
| `scene_ir.json` | 中间表示 |
| `risk_report.json` | 风险分析 |
| `generated.py` | 当前轮生成代码 |
| `stdout.log` | 当前轮标准输出 |
| `stderr.log` | 当前轮错误输出 |
| `render_report.json` | 渲染报告 |
| `issues.json` | 错误诊断结果 |
| `repair_decision.json` | 修复决策 |
| `validation.json` | 修复有效性验证 |
| `final_result.json` | 最终响应结果 |

---

## 11. 使用建议

### 11.1 开发阶段建议

- 先用 `OSS_ENABLED=false` 本地调通
- 先确保 `manim`、`ffmpeg`、`ffprobe` 已进入 PATH
- 使用 `sample_request.json` 作为最小验证请求

### 11.2 生产阶段建议

- 使用真正的 LLM 接口替换当前 mock 模式
- OSS 建议改为 STS 临时凭证
- 对渲染任务增加超时、监控和资源隔离
- 将同步接口扩展为异步任务队列模式

---

## 12. 版本兼容说明

当前代码默认围绕以下约定设计：

- Python 3.11+
- FastAPI
- LangGraph 工作流调度
- Manim Community v0.20.1 目标场景
- 阿里云 OSS 上传

---

## 13. 附录：最小请求模板

```json
{
  "projectBrief": {
    "style": "极简科技感",
    "manimVersion": "0.20.1",
    "videoSpec": {
      "aspectRatio": "16:9",
      "resolution": "1920x1080",
      "fps": 30,
      "background": "#0B1020"
    },
    "subtitleSpec": {
      "enabled": true,
      "position": "bottom",
      "maxLines": 2,
      "fontSize": 30
    },
    "designRules": []
  },
  "timedScenes": [
    {
      "sceneId": "SC001",
      "durationSec": 3,
      "sentences": [],
      "subtitleItems": [],
      "animationCues": [],
      "sceneSpec": {
        "layoutTemplate": "center_focus",
        "objects": []
      }
    }
  ]
}
```

---

## 14. 联系说明

如果后续你继续扩展这个服务，建议下一步把文档拆成两份：

1. **对外 API 文档**
2. **内部工作流 / LangGraph 状态机文档**

这样前后端、算法、平台三方都更好协作。
