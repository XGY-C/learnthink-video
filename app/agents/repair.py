from __future__ import annotations

import json
import logging
import re
from app.llm.base import BaseLLMClient
from app.agents.notice_redlines import build_notice_redlines
from app.models.issues import RepairDecision
from app.tools.manim_doc_search import ManimDocSearchTool, SearchQuery


logger = logging.getLogger(__name__)


class RepairAgent:
    def __init__(
        self,
        llm_client: BaseLLMClient | None = None,
        enable_llm_fallback: bool = False,
        doc_search_tool: ManimDocSearchTool | None = None,
    ) -> None:
        self.llm_client = llm_client
        self.enable_llm_fallback = enable_llm_fallback
        self.doc_search_tool = doc_search_tool

    @staticmethod
    def _strip_mathtex_text_segments(code: str) -> tuple[str, bool]:
        # Remove \text{...} arguments from MathTex(...) to avoid CJK latex compile failures.
        patched = re.sub(r',\s*"\\\\text\{[^"{}]+}"', "", code)
        return patched, patched != code

    @staticmethod
    def _extract_python_code(response: str) -> str:
        text = (response or "").strip()
        if not text:
            return ""
        fenced = re.search(r"```(?:python)?\s*(.*?)```", text, re.DOTALL | re.IGNORECASE)
        if fenced:
            return fenced.group(1).strip()
        return text

    @staticmethod
    def _rewrite_axes_size_kwargs(code: str) -> tuple[str, bool]:
        marker = re.compile(r"\bAxes\s*\(")
        out: list[str] = []
        cursor = 0
        changed = False

        for match in marker.finditer(code):
            out.append(code[cursor:match.end()])
            i = match.end()
            depth = 1
            quote: str | None = None
            escaped = False
            while i < len(code):
                ch = code[i]
                if quote is not None:
                    if escaped:
                        escaped = False
                    elif ch == "\\":
                        escaped = True
                    elif ch == quote:
                        quote = None
                else:
                    if ch in {"\"", "'"}:
                        quote = ch
                    elif ch == "(":
                        depth += 1
                    elif ch == ")":
                        depth -= 1
                        if depth == 0:
                            break
                i += 1

            if i >= len(code):
                out.append(code[match.end():])
                cursor = len(code)
                break

            args = code[match.end():i]
            rewritten = re.sub(r"(?<!\w)height\s*=", "y_length=", args)
            rewritten = re.sub(r"(?<!\w)width\s*=", "x_length=", rewritten)
            if rewritten != args:
                changed = True
            out.append(rewritten)
            out.append(")")
            cursor = i + 1

        out.append(code[cursor:])
        patched = "".join(out)
        return patched, changed

    def _try_llm_repair(self, code: str, issues: list[dict], attempt_no: int, notices: list[dict] | None = None, doc_context: str = "") -> tuple[str | None, dict]:
        trace = {
            "llmAttempted": False,
            "llmUsed": False,
            "reason": None,
        }
        if not self.enable_llm_fallback:
            trace["reason"] = "llm_fallback_disabled"
            return None, trace
        if self.llm_client is None:
            trace["reason"] = "llm_client_unavailable"
            return None, trace

        trace["llmAttempted"] = True

        redlines = build_notice_redlines(notices or [])
        redline_block = (
            "Hard constraints from validated failure history. If any preference conflicts with these constraints, constraints win.\n"
            f"{redlines}\n\n"
            if redlines
            else ""
        )
        
        # 构建文档参考部分
        doc_reference_block = ""
        if doc_context:
            doc_reference_block = (
                "CRITICAL: The following official Manim documentation excerpts are highly relevant "
                "to the issues you need to fix. You MUST carefully review this information and "
                "ensure your repaired code complies with the documented API:\n\n"
                f"{doc_context}\n\n"
                "IMPORTANT INSTRUCTIONS:\n"
                "1. Check the documented parameter names and use them correctly\n"
                "2. Follow the API usage patterns shown in the documentation\n"
                "3. If the documentation shows a different approach than the current code, prefer the documented approach\n"
                "4. Cite specific documentation sections when making changes\n\n"
            )
            logger.info(
                "[repair] passing structured doc context to LLM (length: %d chars, will influence repair)",
                len(doc_context),
            )

        system_prompt = (
            "You are an expert Manim Python repair agent. "
            "Repair the provided Python code to resolve runtime issues. "
            "Return only a complete runnable Python file.\n\n"
            "Guidelines:\n"
            "- Make minimal changes to fix the specific issues\n"
            "- Preserve the original scene intent and behavior\n"
            "- Ensure all imports are present (from manim import *, from typing import Dict, List)\n"
            "- Use safe_duration() for all animation run_time values\n"
            "- For LaTeX errors: prefer Text() over MathTex() for non-formula content\n"
            "- For Axes errors: use y_length/x_length instead of height/width\n"
            "- Follow validated notices constraints if provided\n\n"
            "Output requirements:\n"
            "- Must include: from manim import *, class definition, all helper functions\n"
            "- Code must be directly executable without modifications"
            + ("\n\n" + redline_block if redline_block else "")
        )
        user_prompt = (
            f"Attempt: {attempt_no}\n"
            "Task: fix the code for the listed issues while preserving behavior and scene intent.\n"
            "If issue mentions latex/dvi, avoid unsupported MathTex \\text{...} for CJK text and prefer Text for plain language labels.\n\n"
            + (f"Redlines:\n{redlines}\n\n" if redlines else "")
            + (doc_reference_block if doc_reference_block else "")
            +
            f"Issues:\n{json.dumps(issues, ensure_ascii=False)}\n\n"
            f"CurrentCode:\n{code}"
        )
        try:
            response = self.llm_client.complete(system_prompt=system_prompt, user_prompt=user_prompt)
        except Exception as exc:
            trace["reason"] = f"llm_exception:{exc}"
            return None, trace

        repaired = self._extract_python_code(response)
        trace["responseChars"] = len(response or "")
        if not repaired:
            trace["reason"] = "llm_empty_response"
            return None, trace
        if "from manim import" not in repaired or "class " not in repaired:
            trace["reason"] = "llm_response_missing_structure"
            return None, trace
        trace["llmUsed"] = True
        return repaired, trace

    def run(self, code: str, issues: list[dict], attempt_no: int, notices: list[dict] | None = None) -> dict:
        current_code = code
        target_ids: list[str] = []
        summary: list[str] = []
        strategy = "No-op repair"
        expected = "No changes"
        escalate = False
        fallback_attempted = False
        fallback_used = False
        fallback_reason = None
        llm_trace = {
            "escalated": False,
            "llmAttempted": False,
            "llmUsed": False,
            "reason": "not_escalated",
        }
        
        # 如果有文档搜索工具，先搜索相关文档并收集上下文
        doc_context = ""
        if self.doc_search_tool:
            logger.info("[repair] searching documentation for %d issues", len(issues))
            all_docs = []
            for issue in issues:
                search_queries = self._generate_search_queries_from_issue(issue)
                for query_text in search_queries:
                    logger.info(
                        "[repair] searching docs for issue=%s query='%s'",
                        issue["issueId"],
                        query_text,
                    )
                    docs = self.doc_search_tool.search_simple(query_text, max_results=2)
                    if docs:
                        logger.info(
                            "[repair] issue=%s found_docs=%d top_result_score=%.2f source=%s",
                            issue["issueId"],
                            len(docs),
                            docs[0]["relevance_score"],
                            docs[0]["source_type"],
                        )
                        all_docs.extend(docs)
            
            # 去重并构建文档上下文
            if all_docs:
                seen = set()
                unique_docs = []
                for doc in all_docs:
                    key = (doc["source_path"], doc["content"][:100])
                    if key not in seen:
                        seen.add(key)
                        unique_docs.append(doc)
                
                # 按相关性排序，取前5个
                unique_docs.sort(key=lambda x: x["relevance_score"], reverse=True)
                top_docs = unique_docs[:5]
                
                # 按类型分组展示
                doc_groups = {}
                for doc in top_docs:
                    source_type = doc.get("source_type", "unknown")
                    if source_type not in doc_groups:
                        doc_groups[source_type] = []
                    doc_groups[source_type].append(doc)
                
                # 构建结构化上下文
                context_parts = []
                context_parts.append("=" * 60)
                context_parts.append("RELEVANT MANIM DOCUMENTATION FOR REPAIR")
                context_parts.append("=" * 60)
                context_parts.append("")
                
                for source_type, docs in doc_groups.items():
                    context_parts.append(f"[{source_type.upper()} DOCUMENTS]")
                    context_parts.append("-" * 40)
                    
                    for i, doc in enumerate(docs, 1):
                        context_parts.append(f"\n[Doc {i}] Source: {doc['source_path']}")
                        context_parts.append(f"Relevance Score: {doc['relevance_score']:.2f}")
                        context_parts.append(f"Content Preview:")
                        context_parts.append(doc['content'][:400])  # 从800降到400
                        context_parts.append("")
                    
                    context_parts.append("")
                
                context_parts.append("=" * 60)
                context_parts.append("INSTRUCTIONS:")
                context_parts.append("Use the above documentation to guide your repair decisions.")
                context_parts.append("Pay special attention to API signatures and parameter names.")
                context_parts.append("=" * 60)
                
                doc_context = "\n".join(context_parts)
                logger.info(
                    "[repair] built structured doc context with %d unique docs (total length: %d chars)",
                    len(top_docs),
                    len(doc_context),
                )

        for issue in issues:
            target_ids.append(issue["issueId"])
            root = issue["rootCauseLabel"]
            normalized_message = (issue.get("normalizedMessage") or "").lower()

            if root == "invalid_run_time":
                strategy = "Clamp animation durations with safe_duration"
                expected = "Remove non-positive run_time values"
                current_code = re.sub(r"run_time\s*=\s*0(\.0+)?", "run_time=safe_duration(0.2)", current_code)
                summary.append("Replaced zero run_time literals with safe_duration(0.2)")
            elif root == "undefined_name":
                missing_name = issue["normalizedMessage"]
                if "WHITE" in missing_name and "from manim import *" not in current_code:
                    current_code = "from manim import *\n" + current_code
                    strategy = "Ensure Manim wildcard imports exist"
                    expected = "Resolve undefined Manim names"
                    summary.append("Prepended from manim import *")
                else:
                    strategy = "Inject defensive fallback import/header"
                    expected = "Reduce undefined names"
                    if "from manim import *" not in current_code:
                        current_code = "from manim import *\n" + current_code
                        summary.append("Prepended from manim import *")
            elif root == "missing_import":
                strategy = "Inject missing typing import"
                expected = "Resolve missing import issues"
                if "from typing import Dict, List" not in current_code:
                    current_code = current_code.replace(
                        "from manim import *",
                        "from manim import *\nfrom typing import Dict, List",
                    )
                    summary.append("Added typing imports")
            elif root == "missing_module":
                strategy = "Keep repair minimal and surface missing dependency"
                expected = "No code change; dependency should be installed"
                summary.append("No code patch applied for external missing module")
            elif root == "value_error" and "latex error converting to dvi" in (issue.get("normalizedMessage", "").lower()):
                strategy = "Fallback from MathTex text segments for latex compatibility"
                expected = "Avoid latex failures caused by unsupported text in MathTex"
                current_code, changed = self._strip_mathtex_text_segments(current_code)
                if changed:
                    summary.append("Removed \\text{...} segments from MathTex calls")
                else:
                    escalate = True
                    summary.append("No matching MathTex \\text{...} segment found; recommend LLM/tool repair")
            elif root in {"invalid_keyword_in_mobject_initialization", "unexpected_height_kwarg_in_axes_init"} or (
                "unexpected keyword argument" in normalized_message and ("'height'" in normalized_message or "'width'" in normalized_message)
            ):
                strategy = "Normalize Axes size kwargs for Manim compatibility"
                expected = "Replace Axes(height/width) with y_length/x_length"
                current_code, changed = self._rewrite_axes_size_kwargs(current_code)
                if changed:
                    summary.append("Rewrote Axes(height/width) kwargs to y_length/x_length")
                else:
                    escalate = True
                    summary.append("No Axes(height/width) pattern found; recommend LLM/tool repair")
            
            # P0: Manim 特定错误修复
            elif root == "animate_non_mobject":
                strategy = "Wrap non-mobject primitives in appropriate Mobject wrappers"
                expected = "Convert raw values to Mobjects before animation"
                # 尝试将原始值包装为 Mobject
                current_code = re.sub(r"FadeIn\((\d+(?:\.\d+)?)\)", r"FadeIn(Number(\1))", current_code)
                current_code = re.sub(r"FadeOut\((\d+(?:\.\d+)?)\)", r"FadeOut(Number(\1))", current_code)
                current_code = re.sub(r"Create\((\d+(?:\.\d+)?)\)", r"Create(Number(\1))", current_code)
                summary.append("Wrapped numeric literals in Number() mobjects")
            
            elif root == "latex_compilation_failed":
                strategy = "Replace MathTex with Text for non-math content"
                expected = "Use Text() for plain language, MathTex() only for formulas"
                current_code, changed = self._strip_mathtex_text_segments(current_code)
                if changed:
                    summary.append("Removed \\text{...} segments from MathTex calls")
                else:
                    # 如果没有 \text{}，可能是其他 LaTeX 问题，尝试更激进的修复
                    if "MathTex(" in current_code:
                        # 提示使用 Text 替代
                        summary.append("LaTeX compilation failed; consider replacing MathTex with Text for non-formula content")
                        escalate = True
                    else:
                        escalate = True
                        summary.append("LaTeX error detected but no MathTex found; check LaTeX installation")
            
            elif root == "incompatible_mobject_transform":
                strategy = "Ensure compatible mobject types for Transform animations"
                expected = "Transform requires same type (e.g., Circle to Circle, not Circle to Square)"
                escalate = True  # 需要 LLM 智能分析并修复
                summary.append("Transform between incompatible mobject types; requires manual fix")
            
            elif root == "missing_key_reference":
                strategy = "Fix object reference errors"
                expected = "Ensure all target_refs point to existing objects"
                # 这通常在规划阶段就应该检测到，如果到这里说明规划有漏
                escalate = True
                summary.append("Referenced object not found; check object IDs in animation cues")
            
            elif root == "index_out_of_range":
                strategy = "Fix index out of range errors"
                expected = "Ensure array/list indices are within bounds"
                escalate = True
                summary.append("Index out of range; check list/array access in code")
            
            elif root == "manim_runtime_error":
                strategy = "Handle Manim runtime error"
                expected = "Resolve Manim-specific runtime issues"
                escalate = True  # ManimError 通常需要具体分析
                summary.append(f"Manim runtime error: {issue.get('normalizedMessage', 'unknown')}")
            
            # P1: 环境错误
            elif root == "ffmpeg_related":
                strategy = "Surface FFmpeg environment issue"
                expected = "FFmpeg must be installed and accessible"
                # 无法通过代码修复，需要环境干预
                summary.append("FFmpeg error detected; ensure ffmpeg is installed and in PATH")
            
            elif root == "insufficient_memory":
                strategy = "Reduce memory usage"
                expected = "Optimize scene complexity or increase available memory"
                escalate = True
                summary.append("Memory error; reduce scene complexity or increase system memory")
            
            elif root == "disk_full":
                strategy = "Free disk space"
                expected = "Clear temporary files or expand storage"
                # 无法通过代码修复
                summary.append("Disk full; free up space or clear temporary files")
            
            else:
                strategy = "Generic repair guard"
                expected = "Make runtime safer"
                if "def safe_duration" not in current_code:
                    current_code = (
                        "from manim import *\n"
                        "def safe_duration(value: float, fps: int = 30) -> float:\n"
                        "    return max(float(value), 1.0 / max(fps, 1))\n\n"
                    ) + current_code
                    summary.append("Inserted generic safe_duration helper")
                else:
                    escalate = True
                    summary.append("Generic guard already present; escalate to LLM fallback for targeted fix")

        if escalate:
            fallback_attempted = True
            llm_trace["escalated"] = True
            llm_code, llm_trace_result = self._try_llm_repair(
                current_code, issues, attempt_no, notices=notices, doc_context=doc_context
            )
            llm_trace.update(llm_trace_result)
            fallback_reason = llm_trace.get("reason")
            if llm_code and llm_code != current_code:
                current_code = llm_code
                fallback_used = True
                strategy = "LLM fallback repair"
                expected = "Resolve non-trivial issues not covered by deterministic rules"
                summary.append("Applied LLM fallback patch")
                llm_trace["reason"] = None

        decision = RepairDecision(
            attemptNo=attempt_no,
            targetIssueIds=target_ids,
            fixStrategy=strategy,
            expectedOutcome=expected,
            patchSummary=summary or ["No patch applied"],
        )

        return {
            "code": current_code,
            "llmTrace": llm_trace,
            "metadata": {
                **decision.model_dump(by_alias=True),
                "changed": current_code != code,
                "progressHint": "progress" if current_code != code else "no_change",
                "escalate": escalate,
                "fallbackAttempted": fallback_attempted,
                "fallbackUsed": fallback_used,
                "fallbackReason": fallback_reason,
            },
        }
    
    def _generate_search_queries_from_issue(self, issue: dict) -> list[str]:
        """从 issue 生成搜索查询（优化版：最多10个）"""
        queries = []
        root_cause = issue.get("rootCauseLabel", "")
        message = issue.get("normalizedMessage", "").lower()
        code_snippet = issue.get("codeSnippet", "")
        
        # 规则1: 无效参数错误 → 提取参数名和类名
        if "invalid_keyword" in root_cause or "unexpected" in message:
            param_match = re.search(r"'(\w+)'", message)
            class_match = re.search(r'(\w+)\.__init__', message)
            if param_match:
                param_name = param_match.group(1)
                queries.append(f"{param_name} parameter")
                queries.append(f"{param_name} kwarg")
                if class_match:
                    class_name = class_match.group(1)
                    queries.append(f"{class_name} {param_name}")
        
        # 规则2: 未定义名称 → 直接使用名称并添加上下文
        elif "undefined_name" in root_cause:
            name = issue.get("normalizedMessage", "")
            if name:
                queries.append(name)
                queries.append(f"{name} manim")
        
        # 规则3: LaTeX 错误 → 搜索 MathTex CJK 和 Text
        elif "latex" in message or "mathtex" in message:
            queries.append("MathTex CJK text")
            queries.append("Tex Chinese characters")
            queries.append("MathTex vs Text")
        
        # 规则4: 坐标轴相关 → 搜索 Axes 和相关参数
        elif "axes" in message or "coordinate" in message:
            queries.append("Axes")
            queries.append("coordinate system")
            queries.append("Axes parameters")
        
        # 规则5: 动画相关错误
        elif "animation" in message or "mobject" in message:
            queries.append("Animation Mobject")
            queries.append("Transform animation")
        
        # 规则6: 从代码片段提取线索
        if code_snippet:
            # 提取类名
            class_names = re.findall(r'(\w+)\(', code_snippet)
            for class_name in class_names[:2]:  # 只取前2个
                if class_name not in ["self", "print", "len", "range"]:
                    queries.append(class_name)
                    break  # 只添加一个最有价值的
        
        # 规则7: 添加通用查询
        if root_cause:
            queries.append(root_cause)
        
        # 去重并限制数量（保持顺序）
        unique_queries = list(dict.fromkeys(queries))
        return unique_queries[:10]  # 最多10个查询
