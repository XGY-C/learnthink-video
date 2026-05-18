from __future__ import annotations

import json
import logging
import re
from typing import Any

from app.llm.base import BaseLLMClient

logger = logging.getLogger(__name__)


class NoticeSummarizer:
    def __init__(self, llm_client: BaseLLMClient, enabled: bool) -> None:
        self.llm_client = llm_client
        self.enabled = enabled

    def summarize(self, previous_issues: list[dict], new_issues: list[dict], base_rule: str) -> dict[str, Any]:
        cleaned_base_rule = self.clean_rule(base_rule)
        primary = previous_issues[0] if previous_issues else {}
        issue_type = str(primary.get("rootCauseLabel") or "unknown_issue").strip() or "unknown_issue"
        message = str(primary.get("normalizedMessage") or "已识别到可复现的渲染错误模式").strip()
        fallback = {
            "essence": f"该问题属于 {issue_type} 类型，通常由同类模式反复触发。",
            "root_cause": message,
            "never_do": ["不要在未确认根因前反复试错同一路径。"],
            "guardrails": [cleaned_base_rule] if cleaned_base_rule else ["先做根因分类，再应用对应修复策略。"],
            "trigger_signals": [message],
            "preferred_pattern": cleaned_base_rule or "先定位根因，再使用与内容类型匹配的实现方式。",
            "confidence": 0.75,
            "source": "heuristic",
        }
        if not self.enabled:
            return fallback

        prompt_payload = {
            "resolvedIssues": previous_issues,
            "remainingIssues": new_issues,
            "baseRule": base_rule,
            "outputSchema": {
                "essence": "中文描述这类错误的本质机制",
                "root_cause": "中文描述本次主要根因",
                "never_do": ["中文描述下次明确不能再做的行为"],
                "guardrails": ["中文描述可执行的预防原则"],
                "trigger_signals": ["中文描述可快速识别该问题的信号"],
                "preferred_pattern": "中文描述优先实现模式，可作为最终规则",
                "confidence": "0到1之间的小数",
            },
        }

        try:
            content = self.llm_client.complete(
                system_prompt=(
                    "你负责将渲染失败经验沉淀为中文规则。\n\n"
                    "输出要求：\n"
                    "- 只返回严格 JSON，不要包含任何解释性文字\n"
                    "- 键必须为: essence, root_cause, never_do, guardrails, trigger_signals, preferred_pattern, confidence\n\n"
                    "字段说明：\n"
                    "- essence: 中文描述这类错误的本质机制（1-2句话）\n"
                    "- root_cause: 中文描述本次主要根因\n"
                    "- never_do: 数组，中文描述下次明确不能再做的行为（1-3条）\n"
                    "- guardrails: 数组，中文描述可执行的预防原则（1-3条）\n"
                    "- trigger_signals: 数组，中文描述可快速识别该问题的信号（1-3条）\n"
                    "- preferred_pattern: 中文描述优先实现模式，可作为最终规则（1-2句话）\n"
                    "- confidence: 0到1之间的小数，表示规则的可靠程度\n\n"
                    "示例输出：\n"
                    '{"essence":"LaTeX编译失败通常由MathTex中的中文文本引起",'
                    '"root_cause":"MathTex不支持CJK字符",'
                    '"never_do":["不要在MathTex中放中文文本"],'
                    '"guardrails":["中文内容使用Text()渲染"],'
                    '"trigger_signals":["latex error converting to dvi"],'
                    '"preferred_pattern":"遇到中文文本时使用Text()而非MathTex()",'
                    '"confidence":0.9}'
                ),
                user_prompt=json.dumps(prompt_payload, ensure_ascii=False),
            )
            data = self._try_parse_json(content)
            if not data:
                return fallback

            essence = self.clean_rule(str(data.get("essence") or fallback["essence"]))
            root_cause = self.clean_rule(str(data.get("root_cause") or fallback["root_cause"]))
            never_do = self._clean_list(data.get("never_do")) or fallback["never_do"]
            guardrails = self._clean_list(data.get("guardrails")) or fallback["guardrails"]
            trigger_signals = self._clean_list(data.get("trigger_signals")) or fallback["trigger_signals"]
            preferred_pattern = self.clean_rule(str(data.get("preferred_pattern") or fallback["preferred_pattern"]))
            if not preferred_pattern:
                preferred_pattern = fallback["preferred_pattern"]
            confidence_raw = data.get("confidence", fallback["confidence"])
            confidence = float(confidence_raw)
            confidence = max(0.0, min(1.0, confidence))
            return {
                "essence": essence or fallback["essence"],
                "root_cause": root_cause or fallback["root_cause"],
                "never_do": never_do,
                "guardrails": guardrails,
                "trigger_signals": trigger_signals,
                "preferred_pattern": preferred_pattern,
                "confidence": confidence,
                "source": "llm",
            }
        except Exception:
            return fallback

    @staticmethod
    def clean_rule(rule: str) -> str:
        text = (rule or "").strip()
        if not text:
            return ""

        text = re.sub(r"```[\s\S]*?```", " ", text)
        text = text.replace("`", "")
        text = re.sub(r"^[\s>*#-]+", "", text)
        text = re.sub(r"^\d+[\).、]\s*", "", text)
        text = re.sub(r"\s+", " ", text)
        return text.strip(" '\"[]()")

    @staticmethod
    def _try_parse_json(text: str) -> dict[str, Any] | None:
        raw = (text or "").strip()
        if not raw:
            return None
        try:
            parsed = json.loads(raw)
            return parsed if isinstance(parsed, dict) else None
        except json.JSONDecodeError:
            return None

    @classmethod
    def _clean_list(cls, raw: Any) -> list[str]:
        if not isinstance(raw, list):
            return []
        cleaned = [cls.clean_rule(str(item)) for item in raw]
        return [item for item in cleaned if item]

