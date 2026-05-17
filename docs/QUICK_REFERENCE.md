# ManimDocSearchTool 快速参考

## 🚀 一分钟上手

```python
from app.tools.manim_doc_search import ManimDocSearchTool

# 1. 初始化（~70ms）
tool = ManimDocSearchTool(docs_root="vendor-docs/manim")

# 2. 搜索（<5ms）
results = tool.search_simple("Circle", max_results=3)

# 3. 使用结果
for r in results:
    print(f"{r['source_path']}: {r['relevance_score']}")
```

## 📋 常用查询模式

### API 查找
```python
tool.search_simple("Circle")           # 类名
tool.search_simple("Axes")             # 类名
tool.search_simple("FadeIn")           # 方法名
```

### 参数查询
```python
tool.search_simple("height parameter")
tool.search_simple("y_length kwarg")
```

### 示例查找
```python
tool.search_simple("SquareToCircle")   # 场景名
tool.search_simple("Transform animation")
tool.search_simple("Create Circle")
```

### 错误解决
```python
# 从 issue 自动生成查询
issue = {
    "rootCauseLabel": "invalid_keyword_in_mobject_initialization",
    "normalizedMessage": "unexpected keyword argument 'height'",
}
queries = repair_agent._generate_search_queries_from_issue(issue)
# → ["height parameter", "height kwarg"]
```

## 🔧 高级用法

### 自定义策略
```python
from app.tools.manim_doc_search import SearchQuery, SearchStrategy

query = SearchQuery(
    query_text="how to create coordinate system",
    strategy=SearchStrategy.EXAMPLE_BASED,
    max_results=5,
)
results = tool.search(query)
```

### 启用语义搜索
```python
tool = ManimDocSearchTool(
    docs_root="vendor-docs/manim",
    enable_semantic_search=True,  # 需要 chromadb + sentence-transformers
)
```

## 📊 返回结果格式

```python
{
    "content": "...",              # 文档内容（最多2000字符）
    "source_type": "api_reference", # 来源类型
    "source_path": "manim/mobject/...",  # 文件路径
    "relevance_score": 0.95,       # 相关性评分 (0-1)
    "strategy_used": "exact_match", # 使用的策略
    "metadata": {...}              # 额外信息
}
```

## 🎯 策略选择规则

| 查询类型 | 自动选择的策略 |
|---------|--------------|
| `Circle` (大写字母开头) | EXACT_MATCH |
| `error`, `exception` | ERROR_RESOLUTION |
| `how to`, `example` | EXAMPLE_BASED |
| 其他 | SEMANTIC (如果启用) |

## 💡 最佳实践

### ✅ 推荐
```python
# 1. 使用简短、具体的查询
tool.search_simple("Axes y_length")

# 2. 限制结果数量
tool.search_simple("Circle", max_results=3)

# 3. 检查返回结果
results = tool.search_simple("Circle")
if results:
    best = results[0]  # 最相关的结果
```

### ❌ 避免
```python
# 1. 过长的自然语言查询
tool.search_simple("How can I create a red circle with blue border?")

# 2. 不限制结果数量
tool.search_simple("animation", max_results=100)

# 3. 忽略空结果
results = tool.search_simple("NonExistentClass")
# results 可能为空列表 []
```

## 🔍 调试技巧

### 查看详细日志
```python
import logging
logging.basicConfig(level=logging.INFO)

# 会输出：
# [doc_search] query='Circle' strategy=exact_match max_results=3
# [doc_search] exact_match found=12
# [doc_search] completed total_results=3 elapsed_ms=1
```

### 检查索引状态
```python
print(f"API entries: {len(tool.exact_match_index)}")
print(f"Examples: {len(tool.example_index)}")
print(f"Semantic: {tool.semantic_enabled}")
```

### 测试特定查询
```python
# 强制使用某种策略
from app.tools.manim_doc_search import SearchStrategy

query = SearchQuery(
    query_text="Circle",
    strategy=SearchStrategy.EXAMPLE_BASED,  # 强制使用示例搜索
)
results = tool.search(query)
```

## ⚡ 性能提示

| 操作 | 耗时 | 优化建议 |
|------|------|---------|
| 初始化 | ~70ms | 应用启动时一次性创建 |
| 精确匹配 | <1ms | 无需优化 |
| 示例搜索 | <5ms | 无需优化 |
| 语义搜索 | 100-200ms | 仅在必要时启用 |

## 🛠️ 常见问题

### Q: 为什么搜索结果为空？
A: 检查查询词是否准确，尝试更通用的关键词

### Q: 如何提高搜索准确性？
A: 使用具体类名或方法名，避免模糊描述

### Q: 可以搜索中文吗？
A: 基础模式不支持，需要启用语义搜索并使用多语言模型

### Q: 如何更新索引？
A: 重新创建工具实例即可自动重新索引

## 📚 更多信息

- 完整文档：`MANIM_DOC_SEARCH_TOOL.md`
- 实现细节：`IMPLEMENTATION_SUMMARY.md`
- 演示脚本：`python demo_doc_search.py`
- 单元测试：`pytest tests/test_manim_doc_search.py -v`
