"""
Manim 官方文档智能搜索工具

设计理念：
- 分层检索：从精确到模糊，逐级fallback
- 缓存优先：高频查询结果缓存，降低延迟
- 上下文感知：根据智能体类型和问题类型调整检索策略
- 可解释性：返回检索来源和置信度，帮助智能体判断
"""

from __future__ import annotations

import json
import logging
import re
import time
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)


class SearchStrategy(Enum):
    """检索策略枚举"""
    EXACT_MATCH = "exact_match"           # 精确匹配（类名、方法名）
    SEMANTIC = "semantic"                 # 语义检索（概念性问题）
    EXAMPLE_BASED = "example_based"       # 示例驱动（如何实现某功能）
    ERROR_RESOLUTION = "error_resolution" # 错误解决（已知错误模式）
    AUTO = "auto"                         # 自动选择策略


@dataclass
class SearchResult:
    """搜索结果"""
    content: str                          # 检索到的内容
    source_type: str                      # 来源类型：api_doc/example/guide/source_code
    source_path: str                      # 原始文件路径
    relevance_score: float                # 相关性评分 (0-1)
    strategy_used: str                    # 使用的检索策略
    metadata: dict = field(default_factory=dict)  # 额外元数据
    
    def to_dict(self) -> dict:
        return {
            "content": self.content[:2000],  # 限制长度避免token溢出
            "source_type": self.source_type,
            "source_path": self.source_path,
            "relevance_score": round(self.relevance_score, 3),
            "strategy_used": self.strategy_used,
            "metadata": self.metadata,
        }


@dataclass
class SearchQuery:
    """搜索查询"""
    query_text: str                       # 查询文本
    strategy: SearchStrategy = SearchStrategy.AUTO
    max_results: int = 5
    filters: dict = field(default_factory=dict)  # 过滤条件
    
    @property
    def is_api_lookup(self) -> bool:
        """判断是否为API查找（类名/方法名）"""
        return bool(re.match(r'^[A-Z][a-zA-Z0-9_]*$', self.query_text.strip()))
    
    @property
    def is_error_query(self) -> bool:
        """判断是否为错误查询"""
        error_keywords = ['error', 'exception', 'failed', 'invalid', 'missing']
        return any(kw in self.query_text.lower() for kw in error_keywords)


class ManimDocSearchTool:
    """
    Manim 官方文档智能搜索工具
    
    使用示例：
        tool = ManimDocSearchTool(docs_root="vendor-docs/manim")
        results = tool.search(SearchQuery(query_text="Axes height width parameters"))
        for result in results:
            print(result.to_dict())
    """
    
    def __init__(
        self,
        docs_root: str | Path,
        cache_dir: str | Path | None = None,
        enable_semantic_search: bool = False,  # 默认关闭，需要时开启
    ) -> None:
        self.docs_root = Path(docs_root)
        self.cache_dir = Path(cache_dir) if cache_dir else self.docs_root.parent / ".doc_search_cache"
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        
        # 初始化组件
        logger.info("[doc_search] initializing exact match index...")
        start_time = time.perf_counter()
        self.exact_match_index = self._build_exact_match_index()
        elapsed_ms = int((time.perf_counter() - start_time) * 1000)
        logger.info(
            "[doc_search] exact match index built: %d entries in %dms",
            len(self.exact_match_index),
            elapsed_ms,
        )
        
        logger.info("[doc_search] indexing example scenes...")
        start_time = time.perf_counter()
        self.example_index = self._index_examples()
        elapsed_ms = int((time.perf_counter() - start_time) * 1000)
        logger.info(
            "[doc_search] example index built: %d examples in %dms",
            len(self.example_index),
            elapsed_ms,
        )
        
        # 语义搜索（可选，需要资源）
        self.semantic_enabled = enable_semantic_search
        if enable_semantic_search:
            self._initialize_semantic_search()
        else:
            self.embedding_model = None
            self.vector_db = None
        
        logger.info(
            "[doc_search] initialized exact_matches=%d examples=%d semantic=%s",
            len(self.exact_match_index),
            len(self.example_index),
            enable_semantic_search,
        )
    
    def _initialize_semantic_search(self) -> None:
        """初始化语义搜索组件"""
        try:
            import chromadb
            from chromadb.config import Settings
            from sentence_transformers import SentenceTransformer
            
            embedding_model_name = "paraphrase-multilingual-MiniLM-L12-v2"
            logger.info("[doc_search] loading embedding model: %s", embedding_model_name)
            self.embedding_model = SentenceTransformer(embedding_model_name)
            
            client = chromadb.PersistentClient(
                path=str(self.cache_dir / "chroma_db"),
                settings=Settings(anonymized_telemetry=False),
            )
            
            collection_name = "manim_docs"
            try:
                self.vector_db = client.get_collection(collection_name)
            except Exception:
                self.vector_db = client.create_collection(
                    name=collection_name,
                    metadata={"description": "Manim documentation embeddings"},
                )
                self._index_documents()
            
            logger.info("[doc_search] semantic search enabled")
            
        except ImportError as e:
            logger.warning(
                "[doc_search] semantic search disabled: missing dependencies (%s). "
                "Install with: pip install chromadb sentence-transformers",
                e,
            )
            self.semantic_enabled = False
            self.embedding_model = None
            self.vector_db = None
    
    def search(self, query: SearchQuery) -> list[SearchResult]:
        """
        执行文档搜索
        
        Args:
            query: 搜索查询对象
            
        Returns:
            按相关性排序的搜索结果列表
        """
        start_time = time.perf_counter()
        strategy = self._select_strategy(query)
        
        logger.info(
            "[doc_search] query='%s' strategy=%s max_results=%d",
            query.query_text,
            strategy.value,
            query.max_results,
        )
        
        results = []
        
        # Layer 1: 精确匹配
        if strategy == SearchStrategy.EXACT_MATCH or strategy == SearchStrategy.AUTO:
            exact_results = self._exact_match_search(query)
            results.extend(exact_results)
            logger.info(
                "[doc_search] exact_match found=%d",
                len(exact_results),
            )
        
        # Layer 2: 语义检索
        if (
            self.semantic_enabled
            and len(results) < query.max_results
            and strategy in {SearchStrategy.SEMANTIC, SearchStrategy.AUTO}
        ):
            semantic_results = self._semantic_search(query)
            results.extend(semantic_results)
            logger.info(
                "[doc_search] semantic found=%d",
                len(semantic_results),
            )
        
        # Layer 3: 示例检索
        if len(results) < query.max_results or strategy == SearchStrategy.EXAMPLE_BASED:
            example_results = self._example_search(query)
            results.extend(example_results)
            logger.info(
                "[doc_search] examples found=%d",
                len(example_results),
            )
        
        # 去重、排序、截断
        results = self._deduplicate_and_rank(results)
        results = results[:query.max_results]
        
        elapsed_ms = int((time.perf_counter() - start_time) * 1000)
        logger.info(
            "[doc_search] completed total_results=%d elapsed_ms=%d",
            len(results),
            elapsed_ms,
        )
        
        return results
    
    def search_simple(self, query_text: str, max_results: int = 5) -> list[dict]:
        """
        简化版搜索接口（供智能体快速调用）
        
        Args:
            query_text: 查询文本
            max_results: 最大返回结果数
            
        Returns:
            字典格式的搜索结果列表
        """
        query = SearchQuery(
            query_text=query_text,
            strategy=SearchStrategy.AUTO,
            max_results=max_results,
        )
        results = self.search(query)
        return [r.to_dict() for r in results]
    
    # ==================== 私有方法 ====================
    
    def _select_strategy(self, query: SearchQuery) -> SearchStrategy:
        """自动选择检索策略"""
        if query.strategy != SearchStrategy.AUTO:
            return query.strategy
        
        if query.is_api_lookup:
            return SearchStrategy.EXACT_MATCH
        elif query.is_error_query:
            return SearchStrategy.ERROR_RESOLUTION
        elif "how to" in query.query_text.lower() or "example" in query.query_text.lower():
            return SearchStrategy.EXAMPLE_BASED
        else:
            return SearchStrategy.SEMANTIC if self.semantic_enabled else SearchStrategy.EXACT_MATCH
    
    def _build_exact_match_index(self) -> dict[str, dict]:
        """
        构建精确匹配索引
        
        从源代码中提取：
        - 类定义及其 docstring
        - 方法签名
        - 关键参数说明
        """
        index = {}
        manim_src = self.docs_root / "manim"
        
        if not manim_src.exists():
            logger.warning("[doc_search] manim source directory not found: %s", manim_src)
            return index
        
        # 扫描所有 Python 文件
        py_files = list(manim_src.rglob("*.py"))
        logger.info("[doc_search] scanning %d Python files for exact match index", len(py_files))
        
        for py_file in py_files:
            try:
                content = py_file.read_text(encoding="utf-8")
                
                # 提取类定义
                class_pattern = re.compile(
                    r'class\s+(\w+)\s*\(([^)]*)\)\s*:\s*(?:\n\s*"""(.*?)""")?',
                    re.DOTALL,
                )
                for match in class_pattern.finditer(content):
                    class_name = match.group(1)
                    base_classes = match.group(2).strip()
                    docstring = match.group(3).strip() if match.group(3) else ""
                    
                    index[class_name] = {
                        "type": "class",
                        "file": str(py_file.relative_to(self.docs_root)),
                        "base_classes": base_classes,
                        "docstring": docstring[:1000],
                        "full_path": str(py_file),
                    }
                
                # 提取函数定义
                func_pattern = re.compile(
                    r'def\s+(\w+)\s*\(([^)]*)\)\s*(?:->\s*[\w\[\],\s]+)?\s*:(?:\n\s*"""(.*?)""")?',
                    re.DOTALL,
                )
                for match in func_pattern.finditer(content):
                    func_name = match.group(1)
                    params = match.group(2).strip()
                    docstring = match.group(3).strip() if match.group(3) else ""
                    
                    key = f"{func_name}"
                    if key not in index:
                        index[key] = {
                            "type": "function",
                            "file": str(py_file.relative_to(self.docs_root)),
                            "params": params,
                            "docstring": docstring[:1000],
                            "full_path": str(py_file),
                        }
                        
            except Exception as e:
                logger.warning("[doc_search] failed to index file %s: %s", py_file, e)
        
        return index
    
    def _index_examples(self) -> list[dict]:
        """索引示例代码"""
        examples = []
        example_dir = self.docs_root / "example_scenes"
        
        if not example_dir.exists():
            logger.warning("[doc_search] example_scenes directory not found: %s", example_dir)
            return examples
        
        py_files = list(example_dir.glob("*.py"))
        logger.info("[doc_search] scanning %d example files", len(py_files))
        
        for py_file in py_files:
            try:
                content = py_file.read_text(encoding="utf-8")
                
                # 提取场景类
                scene_pattern = re.compile(
                    r'class\s+(\w+)\s*\(\s*Scene\s*\)\s*:(.*?)(?=\nclass |\Z)',
                    re.DOTALL,
                )
                
                for match in scene_pattern.finditer(content):
                    scene_name = match.group(1)
                    scene_code = match.group(2).strip()
                    
                    # 提取关键特征
                    features = self._extract_code_features(scene_code)
                    
                    examples.append({
                        "scene_name": scene_name,
                        "file": str(py_file.relative_to(self.docs_root)),
                        "code": scene_code[:3000],  # 限制长度
                        "features": features,
                        "full_path": str(py_file),
                    })
                    
            except Exception as e:
                logger.warning("[doc_search] failed to index example %s: %s", py_file, e)
        
        return examples
    
    def _extract_code_features(self, code: str) -> list[str]:
        """提取代码特征标签"""
        features = []
        
        # 检测使用的动画类型
        animations = re.findall(r'self\.play\((\w+)', code)
        features.extend([f"animation:{anim}" for anim in set(animations)])
        
        # 检测使用的 Mobject 类型
        mobjects = re.findall(r'(\w+)\s*=\s*(Circle|Square|Triangle|Text|Tex|MathTex|VGroup|NumberPlane|DecimalNumber)', code)
        features.extend([f"mobject:{m[1]}" for m in mobjects])
        
        # 检测特殊技术
        if 'add_updater' in code:
            features.append("technique:updater")
        if 'prepare_for_nonlinear_transform' in code:
            features.append("technique:nonlinear_transform")
        if 'arrange' in code:
            features.append("technique:arrange")
        if 'Transform' in code:
            features.append("technique:transform")
        if 'FadeIn' in code or 'FadeOut' in code:
            features.append("technique:fade")
        if 'Create' in code:
            features.append("technique:create")
        if 'Write' in code:
            features.append("technique:write")
        
        return features
    
    def _index_documents(self) -> None:
        """将文档索引到向量数据库"""
        if self.vector_db is None:
            return
        
        if self.vector_db.count() > 0:
            logger.info("[doc_search] vector db already indexed (%d documents), skipping", self.vector_db.count())
            return
        
        documents = []
        metadatas = []
        ids = []
        
        # 索引 RST 文档
        docs_source = self.docs_root / "docs" / "source"
        if docs_source.exists():
            rst_files = list(docs_source.rglob("*.rst"))
            logger.info("[doc_search] indexing %d RST documents", len(rst_files))
            
            for rst_file in rst_files:
                try:
                    content = rst_file.read_text(encoding="utf-8")
                    # 分块处理
                    chunks = self._chunk_document(content, chunk_size=1000, overlap=200)
                    
                    for i, chunk in enumerate(chunks):
                        doc_id = f"{rst_file.stem}_chunk_{i}"
                        documents.append(chunk)
                        metadatas.append({
                            "source_type": "api_doc",
                            "file": str(rst_file.relative_to(self.docs_root)),
                            "chunk_index": i,
                        })
                        ids.append(doc_id)
                        
                except Exception as e:
                    logger.warning("[doc_search] failed to index rst %s: %s", rst_file, e)
        
        # 批量添加
        if documents and self.embedding_model is not None:
            logger.info("[doc_search] generating embeddings for %d document chunks", len(documents))
            embeddings = self.embedding_model.encode(documents).tolist()
            
            self.vector_db.add(
                embeddings=embeddings,
                documents=documents,
                metadatas=metadatas,
                ids=ids,
            )
            logger.info("[doc_search] vector db indexing complete")
    
    def _chunk_document(self, text: str, chunk_size: int = 1000, overlap: int = 200) -> list[str]:
        """文档分块"""
        chunks = []
        start = 0
        
        while start < len(text):
            end = start + chunk_size
            chunk = text[start:end]
            
            # 尝试在句子边界切分
            if end < len(text):
                last_period = chunk.rfind('.\n')
                if last_period > chunk_size * 0.7:
                    chunk = chunk[:last_period + 1]
                    end = start + last_period + 1
            
            chunks.append(chunk.strip())
            start = end - overlap if end < len(text) else len(text)
        
        return chunks
    
    def _exact_match_search(self, query: SearchQuery) -> list[SearchResult]:
        """精确匹配搜索"""
        results = []
        query_stripped = query.query_text.strip()
        
        # 直接类名/方法名匹配
        if query_stripped in self.exact_match_index:
            entry = self.exact_match_index[query_stripped]
            results.append(SearchResult(
                content=f"{entry['type'].upper()}: {query_stripped}\n\n{entry.get('docstring', '')}",
                source_type="api_reference",
                source_path=entry['file'],
                relevance_score=0.95,
                strategy_used=SearchStrategy.EXACT_MATCH.value,
                metadata={"type": entry['type']},
            ))
        
        # 模糊匹配（前缀、包含）
        for key, entry in self.exact_match_index.items():
            if (
                query_stripped.lower() in key.lower()
                or key.lower() in query_stripped.lower()
            ):
                results.append(SearchResult(
                    content=f"{entry['type'].upper()}: {key}\n\n{entry.get('docstring', '')[:500]}",
                    source_type="api_reference",
                    source_path=entry['file'],
                    relevance_score=0.7,
                    strategy_used=SearchStrategy.EXACT_MATCH.value,
                    metadata={"type": entry['type'], "matched_key": key},
                ))
        
        return results
    
    def _semantic_search(self, query: SearchQuery) -> list[SearchResult]:
        """语义搜索"""
        if not self.semantic_enabled or self.vector_db is None or self.embedding_model is None:
            return []
        
        try:
            # 生成查询嵌入
            query_embedding = self.embedding_model.encode(query.query_text).tolist()
            
            # 向量检索
            response = self.vector_db.query(
                query_embeddings=[query_embedding],
                n_results=query.max_results * 2,  # 多取一些用于后续筛选
                include=["documents", "metadatas", "distances"],
            )
            
            results = []
            if response['documents'] and response['documents'][0]:
                for i, doc in enumerate(response['documents'][0]):
                    distance = response['distances'][0][i] if response['distances'] else 1.0
                    metadata = response['metadatas'][0][i] if response['metadatas'] else {}
                    
                    # 距离转换为相似度分数
                    similarity = 1.0 / (1.0 + distance)
                    
                    results.append(SearchResult(
                        content=doc[:2000],
                        source_type=metadata.get('source_type', 'documentation'),
                        source_path=metadata.get('file', 'unknown'),
                        relevance_score=similarity,
                        strategy_used=SearchStrategy.SEMANTIC.value,
                        metadata=metadata,
                    ))
            
            return results
            
        except Exception as e:
            logger.exception("[doc_search] semantic search failed: %s", e)
            return []
    
    def _example_search(self, query: SearchQuery) -> list[SearchResult]:
        """示例代码搜索"""
        results = []
        query_lower = query.query_text.lower()
        
        for example in self.example_index:
            score = 0.0
            
            # 场景名称匹配
            if query_lower in example['scene_name'].lower():
                score += 0.5
            
            # 特征匹配
            matching_features = [
                f for f in example['features']
                if any(term in f for term in query_lower.split())
            ]
            score += len(matching_features) * 0.15
            
            # 代码内容匹配
            if query_lower in example['code'].lower():
                score += 0.3
            
            if score > 0.2:
                results.append(SearchResult(
                    content=f"Example: {example['scene_name']}\n\n```python\n{example['code'][:1500]}\n```",
                    source_type="example",
                    source_path=example['file'],
                    relevance_score=min(score, 1.0),
                    strategy_used=SearchStrategy.EXAMPLE_BASED.value,
                    metadata={
                        "scene_name": example['scene_name'],
                        "features": example['features'],
                    },
                ))
        
        return results
    
    def _deduplicate_and_rank(self, results: list[SearchResult]) -> list[SearchResult]:
        """去重并排序"""
        seen = set()
        unique_results = []
        
        for result in results:
            # 基于内容和来源去重
            key = (result.source_path, result.content[:200])
            if key not in seen:
                seen.add(key)
                unique_results.append(result)
        
        # 按相关性分数降序排序
        unique_results.sort(key=lambda r: r.relevance_score, reverse=True)
        
        return unique_results
