"""
ManimDocSearchTool 单元测试
"""

import logging
from pathlib import Path

import pytest

from app.tools.manim_doc_search import ManimDocSearchTool, SearchQuery, SearchStrategy


logger = logging.getLogger(__name__)


@pytest.fixture
def docs_root() -> Path:
    """获取文档根目录"""
    # 使用项目根目录（tests 的父目录）
    project_root = Path(__file__).parent.parent
    return project_root / "vendor-docs" / "manim"


@pytest.fixture
def search_tool(docs_root: Path) -> ManimDocSearchTool:
    """创建搜索工具实例"""
    return ManimDocSearchTool(
        docs_root=docs_root,
        enable_semantic_search=False,  # 测试时关闭语义搜索
    )


class TestExactMatchIndex:
    """精确匹配索引测试"""
    
    def test_build_index_success(self, search_tool: ManimDocSearchTool):
        """测试索引构建成功"""
        assert len(search_tool.exact_match_index) > 0
        logger.info("Built index with %d entries", len(search_tool.exact_match_index))
    
    def test_find_scene_class(self, search_tool: ManimDocSearchTool):
        """测试查找 Scene 类"""
        if "Scene" in search_tool.exact_match_index:
            entry = search_tool.exact_match_index["Scene"]
            assert entry["type"] == "class"
            logger.info("Found Scene class: %s", entry.get("docstring", "")[:100])
    
    def test_find_circle_class(self, search_tool: ManimDocSearchTool):
        """测试查找 Circle 类"""
        if "Circle" in search_tool.exact_match_index:
            entry = search_tool.exact_match_index["Circle"]
            assert entry["type"] == "class"
            logger.info("Found Circle class")


class TestExampleIndex:
    """示例代码索引测试"""
    
    def test_index_examples_success(self, search_tool: ManimDocSearchTool):
        """测试示例索引构建成功"""
        assert len(search_tool.example_index) > 0
        logger.info("Indexed %d examples", len(search_tool.example_index))
    
    def test_example_has_features(self, search_tool: ManimDocSearchTool):
        """测试示例包含特征标签"""
        for example in search_tool.example_index[:3]:
            assert "scene_name" in example
            assert "features" in example
            assert "code" in example
            logger.info(
                "Example %s has %d features",
                example["scene_name"],
                len(example["features"]),
            )


class TestExactMatchSearch:
    """精确匹配搜索测试"""
    
    def test_exact_class_lookup(self, search_tool: ManimDocSearchTool):
        """测试精确类名查找"""
        query = SearchQuery(query_text="Circle", strategy=SearchStrategy.EXACT_MATCH)
        results = search_tool.search(query)
        
        if results:
            assert results[0].source_type == "api_reference"
            assert results[0].relevance_score >= 0.7
            logger.info("Found Circle: score=%.2f", results[0].relevance_score)
    
    def test_fuzzy_match(self, search_tool: ManimDocSearchTool):
        """测试模糊匹配"""
        query = SearchQuery(query_text="Axes", strategy=SearchStrategy.EXACT_MATCH)
        results = search_tool.search(query)
        
        logger.info("Fuzzy match for 'Axes' found %d results", len(results))
        for result in results[:2]:
            logger.info("  - %s (score=%.2f)", result.source_path, result.relevance_score)


class TestExampleSearch:
    """示例搜索测试"""
    
    def test_search_by_animation(self, search_tool: ManimDocSearchTool):
        """测试按动画类型搜索"""
        query = SearchQuery(
            query_text="Transform animation",
            strategy=SearchStrategy.EXAMPLE_BASED,
        )
        results = search_tool.search(query)
        
        logger.info("Search for 'Transform' found %d examples", len(results))
        for result in results[:2]:
            logger.info("  - %s (score=%.2f)", result.metadata.get("scene_name"), result.relevance_score)
    
    def test_search_by_mobject(self, search_tool: ManimDocSearchTool):
        """测试按 Mobject 类型搜索"""
        query = SearchQuery(
            query_text="Circle Square",
            strategy=SearchStrategy.EXAMPLE_BASED,
        )
        results = search_tool.search(query)
        
        logger.info("Search for 'Circle Square' found %d examples", len(results))


class TestSimpleSearch:
    """简化搜索接口测试"""
    
    def test_simple_api_lookup(self, search_tool: ManimDocSearchTool):
        """测试简单 API 查找"""
        results = search_tool.search_simple("Circle", max_results=3)
        
        assert isinstance(results, list)
        if results:
            assert "content" in results[0]
            assert "source_type" in results[0]
            assert "relevance_score" in results[0]
            logger.info("Simple search returned %d results", len(results))
    
    def test_simple_example_search(self, search_tool: ManimDocSearchTool):
        """测试简单示例搜索"""
        results = search_tool.search_simple("SquareToCircle", max_results=2)
        
        logger.info("Simple search for 'SquareToCircle' returned %d results", len(results))
        for result in results:
            logger.info("  - %s: %.2f", result["source_path"], result["relevance_score"])


class TestSearchQuery:
    """搜索查询测试"""
    
    def test_is_api_lookup(self):
        """测试 API 查找判断"""
        assert SearchQuery(query_text="Circle").is_api_lookup
        assert SearchQuery(query_text="Scene").is_api_lookup
        assert not SearchQuery(query_text="how to create circle").is_api_lookup
    
    def test_is_error_query(self):
        """测试错误查询判断"""
        assert SearchQuery(query_text="invalid keyword error").is_error_query
        assert SearchQuery(query_text="missing import exception").is_error_query
        assert not SearchQuery(query_text="Circle class").is_error_query


class TestSearchStrategy:
    """搜索策略测试"""
    
    def test_auto_strategy_selection(self, search_tool: ManimDocSearchTool):
        """测试自动策略选择"""
        # API 查找应该使用 EXACT_MATCH
        query1 = SearchQuery(query_text="Circle", strategy=SearchStrategy.AUTO)
        strategy1 = search_tool._select_strategy(query1)
        assert strategy1 == SearchStrategy.EXACT_MATCH
        
        # 示例查询应该使用 EXAMPLE_BASED
        query2 = SearchQuery(query_text="how to create animation", strategy=SearchStrategy.AUTO)
        strategy2 = search_tool._select_strategy(query2)
        assert strategy2 == SearchStrategy.EXAMPLE_BASED
        
        logger.info("Strategy selection working correctly")


class TestIntegration:
    """集成测试"""
    
    def test_full_search_workflow(self, search_tool: ManimDocSearchTool):
        """测试完整搜索流程"""
        # 测试不同类型的查询
        test_queries = [
            ("Circle", "API lookup"),
            ("Axes height width", "Parameter query"),
            ("SquareToCircle", "Example lookup"),
            ("Transform animation", "Animation query"),
        ]
        
        for query_text, description in test_queries:
            logger.info("Testing %s: '%s'", description, query_text)
            results = search_tool.search_simple(query_text, max_results=2)
            logger.info("  Found %d results", len(results))
            
            if results:
                logger.info(
                    "  Top result: %s (score=%.2f, type=%s)",
                    results[0]["source_path"],
                    results[0]["relevance_score"],
                    results[0]["source_type"],
                )


class TestEdgeCases:
    """边界情况测试"""
    
    def test_empty_query(self, search_tool: ManimDocSearchTool):
        """测试空查询"""
        results = search_tool.search_simple("", max_results=5)
        logger.info("Empty query returned %d results", len(results))
    
    def test_nonexistent_class(self, search_tool: ManimDocSearchTool):
        """测试不存在的类"""
        results = search_tool.search_simple("NonExistentClass12345", max_results=5)
        logger.info("Non-existent class query returned %d results", len(results))
    
    def test_max_results_limit(self, search_tool: ManimDocSearchTool):
        """测试结果数量限制"""
        results = search_tool.search_simple("animation", max_results=1)
        assert len(results) <= 1
        logger.info("Max results limit enforced: %d results", len(results))


if __name__ == "__main__":
    # 配置日志
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    )
    
    # 运行测试
    pytest.main([__file__, "-v", "-s"])
