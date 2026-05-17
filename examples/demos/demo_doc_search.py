"""
ManimDocSearchTool 使用演示脚本

展示如何使用文档搜索工具来辅助代码修复
"""

import logging
from pathlib import Path

from app.tools.manim_doc_search import ManimDocSearchTool, SearchQuery, SearchStrategy

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)

logger = logging.getLogger(__name__)


def demo_basic_search():
    """基础搜索演示"""
    logger.info("=" * 80)
    logger.info("Demo 1: Basic Search")
    logger.info("=" * 80)
    
    # 初始化工具
    project_root = Path(__file__).parent
    docs_root = project_root / "vendor-docs" / "manim"
    
    tool = ManimDocSearchTool(
        docs_root=docs_root,
        enable_semantic_search=False,
    )
    
    # 测试1: 精确类名查找
    logger.info("\n[Test 1] Exact class lookup: 'Circle'")
    results = tool.search_simple("Circle", max_results=2)
    for i, result in enumerate(results, 1):
        logger.info(f"  Result {i}:")
        logger.info(f"    Source: {result['source_type']} ({result['source_path']})")
        logger.info(f"    Score: {result['relevance_score']}")
        logger.info(f"    Content preview: {result['content'][:150]}...")
    
    # 测试2: 参数查询
    logger.info("\n[Test 2] Parameter query: 'Axes height width'")
    results = tool.search_simple("Axes height width", max_results=3)
    for i, result in enumerate(results, 1):
        logger.info(f"  Result {i}:")
        logger.info(f"    Source: {result['source_type']} ({result['source_path']})")
        logger.info(f"    Score: {result['relevance_score']}")


def demo_example_search():
    """示例代码搜索演示"""
    logger.info("\n" + "=" * 80)
    logger.info("Demo 2: Example Code Search")
    logger.info("=" * 80)
    
    project_root = Path(__file__).parent
    docs_root = project_root / "vendor-docs" / "manim"
    
    tool = ManimDocSearchTool(
        docs_root=docs_root,
        enable_semantic_search=False,
    )
    
    # 测试: 查找 Transform 动画示例
    logger.info("\n[Test] Find Transform animation examples")
    query = SearchQuery(
        query_text="Transform animation",
        strategy=SearchStrategy.EXAMPLE_BASED,
        max_results=2,
    )
    results = tool.search(query)
    
    for i, result in enumerate(results, 1):
        logger.info(f"  Example {i}: {result.metadata.get('scene_name', 'N/A')}")
        logger.info(f"    File: {result.source_path}")
        logger.info(f"    Features: {', '.join(result.metadata.get('features', [])[:5])}")
        logger.info(f"    Score: {result.relevance_score}")
        logger.info(f"    Code preview:\n{result.content[:300]}...")


def demo_error_resolution():
    """错误解决演示"""
    logger.info("\n" + "=" * 80)
    logger.info("Demo 3: Error Resolution")
    logger.info("=" * 80)
    
    project_root = Path(__file__).parent
    docs_root = project_root / "vendor-docs" / "manim"
    
    tool = ManimDocSearchTool(
        docs_root=docs_root,
        enable_semantic_search=False,
    )
    
    # 模拟从 issue 生成查询
    test_issues = [
        {
            "issueId": "ISSUE_001",
            "rootCauseLabel": "invalid_keyword_in_mobject_initialization",
            "normalizedMessage": "unexpected keyword argument 'height'",
        },
        {
            "issueId": "ISSUE_002",
            "rootCauseLabel": "value_error",
            "normalizedMessage": "latex error converting to dvi",
        },
    ]
    
    for issue in test_issues:
        logger.info(f"\n[Issue] {issue['issueId']}: {issue['normalizedMessage']}")
        
        # 生成搜索查询
        queries = []
        root_cause = issue.get("rootCauseLabel", "")
        message = issue.get("normalizedMessage", "").lower()
        
        if "invalid_keyword" in root_cause or "unexpected" in message:
            import re
            param_match = re.search(r"'(\w+)'", message)
            if param_match:
                param_name = param_match.group(1)
                queries.append(f"{param_name} parameter")
                queries.append(f"{param_name} kwarg")
        
        elif "latex" in message or "mathtex" in message:
            queries.append("MathTex CJK text")
            queries.append("Tex Chinese characters")
        
        # 执行搜索
        for query_text in queries:
            logger.info(f"  Searching: '{query_text}'")
            results = tool.search_simple(query_text, max_results=2)
            if results:
                logger.info(f"    Found {len(results)} results")
                logger.info(f"    Top result: {results[0]['source_type']} (score={results[0]['relevance_score']})")
            else:
                logger.info(f"    No results found")


def demo_performance():
    """性能测试演示"""
    logger.info("\n" + "=" * 80)
    logger.info("Demo 4: Performance Test")
    logger.info("=" * 80)
    
    import time
    
    project_root = Path(__file__).parent
    docs_root = project_root / "vendor-docs" / "manim"
    
    # 测试初始化时间
    logger.info("\n[Test 1] Initialization time")
    start = time.perf_counter()
    tool = ManimDocSearchTool(
        docs_root=docs_root,
        enable_semantic_search=False,
    )
    elapsed_ms = int((time.perf_counter() - start) * 1000)
    logger.info(f"  Initialization took {elapsed_ms}ms")
    logger.info(f"  Indexed {len(tool.exact_match_index)} API entries")
    logger.info(f"  Indexed {len(tool.example_index)} examples")
    
    # 测试搜索时间
    logger.info("\n[Test 2] Search latency")
    test_queries = ["Circle", "SquareToCircle", "Axes", "Transform"]
    
    for query_text in test_queries:
        start = time.perf_counter()
        results = tool.search_simple(query_text, max_results=3)
        elapsed_ms = int((time.perf_counter() - start) * 1000)
        logger.info(f"  Query '{query_text}': {elapsed_ms}ms, {len(results)} results")


if __name__ == "__main__":
    logger.info("Starting ManimDocSearchTool Demo\n")
    
    demo_basic_search()
    demo_example_search()
    demo_error_resolution()
    demo_performance()
    
    logger.info("\n" + "=" * 80)
    logger.info("Demo completed successfully!")
    logger.info("=" * 80)
