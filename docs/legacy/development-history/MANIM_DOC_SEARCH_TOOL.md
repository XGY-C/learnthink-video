# Manim 官方文档智能搜索工具

## 📋 概述

`ManimDocSearchTool` 是一个专为修改代码的智能体设计的文档搜索工具，能够从本地 Manim 官方文档中快速检索 API 参考、示例代码和使用指南。

## ✨ 核心特性

### 1. 三层混合检索架构

- **精确匹配层**：类名/方法名直接查找（响应时间 <10ms）
- **示例代码层**：基于特征标签的示例检索
- **语义检索层**（可选）：向量数据库支持的概念性查询

### 2. 智能策略选择

自动根据查询类型选择最佳检索策略：
- API 类名 → 精确匹配
- "how to" 问题 → 示例检索
- 错误消息 → 错误解决模式
- 其他 → 语义检索（如果启用）

### 3. 高度透明

符合用户对执行过程透明性的要求：
- 详细的控制台日志展示每个搜索步骤
- 返回结果包含来源路径和相关性评分
- 可追溯的检索策略和元数据

## 🚀 快速开始

### 基础使用

```python
from app.tools.manim_doc_search import ManimDocSearchTool

# 初始化工具
tool = ManimDocSearchTool(
    docs_root="vendor-docs/manim",
    enable_semantic_search=False,  # 默认关闭
)

# 简单搜索
results = tool.search_simple("Circle", max_results=3)
for result in results:
    print(f"Source: {result['source_path']}")
    print(f"Score: {result['relevance_score']}")
    print(f"Content: {result['content'][:200]}")
```

### 高级搜索

```python
from app.tools.manim_doc_search import SearchQuery, SearchStrategy

# 自定义查询
query = SearchQuery(
    query_text="Transform animation",
    strategy=SearchStrategy.EXAMPLE_BASED,
    max_results=5,
)

results = tool.search(query)
for result in results:
    print(f"Example: {result.metadata.get('scene_name')}")
    print(f"Features: {result.metadata.get('features')}")
```

## 🔧 集成到智能体

### Repair Agent 集成

工具已自动集成到 `RepairAgent` 中：

```python
from app.agents.repair import RepairAgent
from app.tools.manim_doc_search import ManimDocSearchTool

# 初始化工具
doc_search_tool = ManimDocSearchTool(docs_root="vendor-docs/manim")

# 创建带文档搜索的修复智能体
repair_agent = RepairAgent(
    llm_client=llm_client,
    enable_llm_fallback=True,
    doc_search_tool=doc_search_tool,  # 注入工具
)

# 运行时会自动搜索相关文档
result = repair_agent.run(code, issues, attempt_no)
```

### Graph Nodes 自动初始化

在 `app/graph/nodes.py` 中已配置自动初始化：

```python
# GraphNodes.__init__ 中自动创建并注入
doc_search_tool = ManimDocSearchTool(
    docs_root=project_root / "vendor-docs" / "manim",
    enable_semantic_search=False,
)

self.repair_agent = RepairAgent(
    llm_client=llm_client,
    enable_llm_fallback=settings.enable_llm_assist,
    doc_search_tool=doc_search_tool,
)
```

## 📊 性能指标

| 指标 | 数值 | 说明 |
|------|------|------|
| 初始化时间 | ~70ms | 索引 2183 个 API + 22 个示例 |
| 精确匹配搜索 | <1ms | 类名/方法名查找 |
| 示例搜索 | <5ms | 特征匹配 |
| 内存占用 | ~50MB | 仅精确匹配+示例 |
| 语义搜索（如启用） | ~100-200ms | 需要向量嵌入计算 |

## 🧪 测试

运行单元测试：

```bash
python -m pytest tests/test_manim_doc_search.py -v -s
```

运行演示脚本：

```bash
python demo_doc_search.py
```

## 📁 项目结构

```
app/tools/
├── manim_doc_search.py       # 主工具实现
└── __init__.py

tests/
├── test_manim_doc_search.py  # 单元测试
└── ...

vendor-docs/manim/            # Manim 官方文档
├── manim/                    # 源代码（API 参考）
├── example_scenes/           # 示例代码
└── docs/                     # RST 文档

demo_doc_search.py            # 使用演示
```

## 🔍 检索策略详解

### 1. 精确匹配（Exact Match）

从 Manim 源代码中提取：
- 类定义及其 docstring
- 方法签名
- 关键参数说明

**适用场景**：
- 已知类名/方法名
- 查询具体 API 用法

**示例**：
```python
tool.search_simple("Circle")  # 查找 Circle 类
tool.search_simple("Axes")    # 查找 Axes 类
```

### 2. 示例检索（Example-Based）

从 `example_scenes/` 目录索引：
- 场景类代码
- 动画类型标签
- Mobject 类型标签
- 技术特征标签

**适用场景**：
- "如何实现某个效果"
- "寻找 Transform 示例"
- "查看 FadeIn 用法"

**示例**：
```python
tool.search_simple("SquareToCircle")
tool.search_simple("Transform animation")
```

### 3. 语义检索（Semantic，可选）

使用向量数据库进行概念匹配：
- 需要安装 `chromadb` 和 `sentence-transformers`
- 索引 RST 文档内容
- 支持自然语言查询

**启用方法**：
```python
tool = ManimDocSearchTool(
    docs_root="vendor-docs/manim",
    enable_semantic_search=True,  # 开启语义搜索
)
```

**首次启动**会自动索引文档（约 30 秒）。

## 💡 使用技巧

### 1. 从 Issue 生成查询

```python
# Repair Agent 内部自动执行
issue = {
    "rootCauseLabel": "invalid_keyword_in_mobject_initialization",
    "normalizedMessage": "unexpected keyword argument 'height'",
}

# 自动生成查询：["height parameter", "height kwarg"]
queries = repair_agent._generate_search_queries_from_issue(issue)
```

### 2. 组合多种查询

```python
# 对同一个 issue 尝试多个查询
for query_text in ["Axes", "coordinate system", "y_length"]:
    results = tool.search_simple(query_text, max_results=2)
    if results:
        print(f"Found: {results[0]['source_path']}")
```

### 3. 利用元数据过滤

```python
results = tool.search_simple("animation", max_results=10)

# 只保留示例类型的结果
examples = [r for r in results if r['source_type'] == 'example']

# 按相关性排序
examples.sort(key=lambda x: x['relevance_score'], reverse=True)
```

## 🔮 未来扩展

### 计划中的功能

1. **缓存层**：LRU 缓存高频查询结果
2. **错误模式学习**：从历史 issue 中学习常见错误及解决方案
3. **代码差异对比**：返回修复前后的代码对比建议
4. **多语言支持**：支持中文查询（"如何创建坐标轴"）

### 性能优化

- 预计算常用查询结果
- 增量索引更新
- 分布式向量检索（大规模场景）

## 📝 日志示例

工具运行时输出详细日志：

```
2026-05-17 11:26:34,152 [INFO] app.tools.manim_doc_search: [doc_search] initializing exact match index...
2026-05-17 11:26:34,163 [INFO] app.tools.manim_doc_search: [doc_search] scanning 166 Python files for exact match index
2026-05-17 11:26:34,229 [INFO] app.tools.manim_doc_search: [doc_search] exact match index built: 2183 entries in 77ms
2026-05-17 11:26:34,235 [INFO] app.tools.manim_doc_search: [doc_search] query='Circle' strategy=exact_match max_results=2
2026-05-17 11:26:34,236 [INFO] app.tools.manim_doc_search: [doc_search] exact_match found=12
2026-05-17 11:26:34,236 [INFO] app.tools.manim_doc_search: [doc_search] completed total_results=2 elapsed_ms=1
```

## 🤝 贡献

如需改进或添加功能，请参考：
1. 保持详细的日志输出（符合透明性要求）
2. 编写对应的单元测试
3. 更新本文档

## 📄 许可证

本项目遵循原有项目的许可证条款。
