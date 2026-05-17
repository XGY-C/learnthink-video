# 代码生成策略简化说明

## 修改概述

本次修改简化了代码生成流程，移除了双候选对比机制（CodegenSelector），改为基于尝试次数的智能降级策略。

## 修改内容

### 1. 移除的组件

- ❌ **CodegenSelector**：不再进行双候选方案的质量评分和选择
- ❌ **codegen_candidates**：状态中不再保存多个候选方案的对比结果
- ❌ **codegen_selection_rationale**：不再记录选择理由

### 2. 新的代码生成策略

#### 策略逻辑

```python
# 计算失败阈值：当尝试次数超过一半时，切换到确定性模式
fallback_threshold = max(1, max_attempts // 2 + 1)

if attempt_no >= fallback_threshold:
    # 多次失败后，使用 ManimCodeExpert 的确定性代码
    strategy = "manim_code_expert_fallback"
    code = self.code_expert.run(scene_ir)
else:
    # 首次或早期尝试，使用 DirectCodegenAgent（可能使用 LLM）
    strategy = "direct_semantic"
    code = self.direct_codegen.run(scene_ir, notices=notices)
```

#### 示例

假设 `max_attempts = 5`：

| 尝试次数 | 使用的智能体 | 策略名称 | 说明 |
|---------|------------|---------|------|
| Attempt 1 | DirectCodegenAgent | `direct_semantic` | 优先使用 LLM 增强方案 |
| Attempt 2 | DirectCodegenAgent | `direct_semantic` | 继续使用 LLM 增强方案 |
| Attempt 3 | **ManimCodeExpert** | `manim_code_expert_fallback` | ⚠️ 超过阈值，降级到确定性方案 |
| Attempt 4 | **ManimCodeExpert** | `manim_code_expert_fallback` | 使用确定性方案 |
| Attempt 5 | **ManimCodeExpert** | `manim_code_expert_fallback` | 使用确定性方案 |

阈值计算：`fallback_threshold = 5 // 2 + 1 = 3`

### 3. 文件变更清单

#### 修改的文件

1. **app/graph/nodes.py**
   - 移除 `CodegenSelector` 导入和初始化
   - 重写 `generate_code()` 方法，实现基于尝试次数的降级策略
   - 添加详细的日志记录，追踪策略切换

2. **app/graph/state.py**
   - 移除 `codegen_candidates` 字段
   - 移除 `codegen_selection_rationale` 字段

#### 新增的文件

1. **tests/test_simplified_codegen_strategy.py**
   - 测试 ManimCodeExpert 的确定性代码生成
   - 测试 DirectCodegenAgent 的语义化代码生成
   - 测试降级阈值逻辑
   - 测试基于尝试次数的策略选择
   - 验证两个智能体输出的差异

#### 保留的文件

1. **app/agents/codegen_selector.py** - 保留但不再使用（可用于未来扩展）
2. **tests/test_codegen_selector.py** - 保留但不再运行（可作为参考）

### 4. 产物文件变化

#### 之前的产物

```
runtime/tasks/{task_id}/
├── codegen_candidates.json      # 包含两个方案的评分对比
└── direct_codegen_trace.json    # DirectCodegenAgent 的追踪信息
```

#### 现在的产物

```
runtime/tasks/{task_id}/
└── codegen_trace.json           # 统一的追踪信息，包含策略、尝试次数、阈值等
```

#### codegen_trace.json 示例

**早期尝试（使用 DirectCodegenAgent）**：
```json
{
  "strategy": "direct_semantic",
  "attempt_no": 1,
  "fallback_threshold": 3,
  "mode": "llm",
  "llmAttempted": true,
  "llmUsed": true
}
```

**后期尝试（降级到 ManimCodeExpert）**：
```json
{
  "strategy": "manim_code_expert_fallback",
  "attempt_no": 3,
  "fallback_threshold": 3,
  "mode": "deterministic_fallback",
  "reason": "attempt 3 exceeded fallback threshold 3",
  "llmAttempted": false,
  "llmUsed": false
}
```

## 优势分析

### ✅ 优点

1. **简化流程**：去掉了复杂的双候选对比逻辑，代码更清晰
2. **性能提升**：每次只需生成一份代码，减少 50% 的代码生成开销
3. **智能降级**：在 LLM 表现不佳时自动切换到确定性方案
4. **可预测性**：基于尝试次数的降级策略更容易理解和调试
5. **资源节约**：减少了 LLM API 调用次数（后期尝试不再使用 LLM）

### ⚠️ 潜在影响

1. **失去对比优势**：无法在同一轮次中比较两种方案的质量
2. **早期尝试风险**：如果 DirectCodegenAgent 在前几次尝试中生成的代码质量较差，可能需要更多轮次才能成功

### 📊 权衡建议

当前的降级阈值设置为 `max_attempts // 2 + 1`，这意味着：
- 如果 `max_attempts = 3`，则在第 2 次尝试后降级
- 如果 `max_attempts = 5`，则在第 3 次尝试后降级
- 如果 `max_attempts = 10`，则在第 6 次尝试后降级

这个设置平衡了：
- **LLM 探索机会**：给予足够的尝试次数让 LLM 找到好的解决方案
- **确定性保障**：在多次失败后及时切换到可靠的确定性方案

如果需要调整，可以修改 `nodes.py` 中的 `fallback_threshold` 计算公式。

## 测试验证

运行以下命令验证修改：

```bash
# 运行新的测试用例
python -m pytest tests/test_simplified_codegen_strategy.py -v

# 运行所有相关测试
python -m pytest tests/test_code_expert_audio_beats.py tests/test_direct_codegen.py tests/test_simplified_codegen_strategy.py -v
```

所有测试应该通过 ✅

## 迁移指南

### 对于现有任务

- 已完成的任务不受影响
- 进行中的任务会在下次渲染时使用新策略

### 对于监控和日志

关注以下日志关键字：

```
[generate_code] task=xxx attempt=1 < threshold=3, using DirectCodegenAgent
[generate_code] task=xxx attempt=3 >= threshold=3, switching to ManimCodeExpert (deterministic mode)
```

### 对于数据分析

如果需要分析代码生成策略的效果，可以查询：
- `codegen_trace.json` 中的 `strategy` 字段
- 统计不同策略的成功率
- 分析降级发生的频率和时机

## 未来优化方向

1. **动态阈值调整**：根据历史成功率动态调整降级阈值
2. **问题类型感知**：针对不同类型的错误采用不同的降级策略
3. **混合策略**：在某些场景下仍然可以考虑轻量级的方案对比
4. **A/B 测试**：可以通过配置开关来对比新旧策略的效果

## 总结

本次修改将代码生成流程从"双候选竞争"简化为"智能降级"策略：
- **前期**：充分利用 LLM 的智能生成能力
- **后期**：确保有可靠的确定性方案作为保障

这种设计在保证代码质量的同时，提高了系统的效率和可预测性。
