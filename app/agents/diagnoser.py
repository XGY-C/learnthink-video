from __future__ import annotations

import json
import logging
import re
from pathlib import Path

from app.llm.base import BaseLLMClient
from app.models.issues import IssueFingerprint
from app.utils.hash_utils import sha1_text

logger = logging.getLogger(__name__)


class ErrorDiagnoser:
    # 仅保留 100% 确定的 Python 标准错误模式
    # 所有 Manim 特定错误、复杂错误、环境错误都交给 LLM 诊断
    COMMON_PATTERNS = [
        # Python 语法错误（100% 确定）
        (re.compile(r"SyntaxError: (?P<msg>.+)"), "parse", "SyntaxError", "python_syntax_error"),
        
        # Python 导入错误（100% 确定）
        (re.compile(r"ImportError: (?P<msg>.+)"), "import", "ImportError", "missing_import"),
        (re.compile(r"ModuleNotFoundError: (?P<msg>.+)"), "import", "ModuleNotFoundError", "missing_module"),
        
        # Python 名称错误（100% 确定）
        (re.compile(r"NameError: name '(?P<msg>.+)' is not defined"), "runtime", "NameError", "undefined_name"),
        
        # Python 文件不存在（100% 确定）
        (re.compile(r"FileNotFoundError: (?P<msg>.+)"), "runtime", "FileNotFoundError", "missing_file"),
    ]

    def __init__(self, llm_client: BaseLLMClient | None = None, enable_llm_fallback: bool = True) -> None:
        """
        初始化 ErrorDiagnoser
        
        Args:
            llm_client: LLM 客户端（用于诊断非确定性错误）
            enable_llm_fallback: 是否启用 LLM 回退（默认 True，因为大部分错误需要 LLM）
        """
        self.llm_client = llm_client
        self.enable_llm_fallback = enable_llm_fallback

    @staticmethod
    def _extract_json_payload(text: str) -> dict | None:
        raw = (text or "").strip()
        if not raw:
            return None
        fenced = re.search(r"```(?:json)?\s*(.*?)```", raw, re.DOTALL | re.IGNORECASE)
        if fenced:
            raw = fenced.group(1).strip()
        try:
            payload = json.loads(raw)
        except json.JSONDecodeError:
            return None
        return payload if isinstance(payload, dict) else None

    def _try_llm_diagnose(self, stderr: str, stdout: str, exit_code: int | None) -> IssueFingerprint | None:
        if not self.enable_llm_fallback or self.llm_client is None:
            return None

        system_prompt = (
            "You are a runtime error diagnoser for Manim Python execution logs. "
            "Return strict JSON only with keys: stage, errorType, rootCauseLabel, normalizedMessage, confidence, evidenceLines.\n\n"
            "Guidelines:\n"
            "- stage must be one of: parse, import, runtime, render, ffmpeg\n"
            "- confidence should be 0.7-0.9 for LLM diagnosis\n"
            "- Focus on Manim-specific errors (e.g., animation_target_not_mobject, latex_compilation_failed, axes_invalid_kwargs)\n"
            "- Extract the core error message, avoid verbose explanations\n\n"
            "Example output:\n"
            '{"stage":"runtime","errorType":"TypeError","rootCauseLabel":"animate_non_mobject",'
            '"normalizedMessage":"Animation only works on Mobjects","confidence":0.85,'
            '"evidenceLines":["TypeError: Animation only works on Mobjects"]}'
        )
        user_prompt = json.dumps(
            {
                "exitCode": exit_code,
                "stderrTail": "\n".join((stderr or "").splitlines()[-80:]),
                "stdoutTail": "\n".join((stdout or "").splitlines()[-30:]),
                "constraints": {
                    "stage": ["parse", "import", "runtime", "render", "ffmpeg"],
                    "confidenceRange": [0.0, 1.0],
                    "rootCauseLabelExample": "animation_target_not_mobject",
                },
            },
            ensure_ascii=False,
        )
        try:
            response = self.llm_client.complete(system_prompt=system_prompt, user_prompt=user_prompt)
        except Exception:
            return None

        parsed = self._extract_json_payload(response)
        if not parsed:
            return None

        stage = str(parsed.get("stage") or "").strip().lower()
        error_type = str(parsed.get("errorType") or "").strip()
        root_label = str(parsed.get("rootCauseLabel") or "").strip().lower()
        message = str(parsed.get("normalizedMessage") or "").strip()
        if stage not in {"parse", "import", "runtime", "render", "ffmpeg"}:
            return None
        if not error_type or not root_label or not message:
            return None

        try:
            confidence = float(parsed.get("confidence", 0.7))
        except (TypeError, ValueError):
            confidence = 0.7
        confidence = max(0.0, min(1.0, confidence))

        evidence_raw = parsed.get("evidenceLines")
        evidence_lines = [str(item).strip() for item in evidence_raw] if isinstance(evidence_raw, list) else []
        evidence_lines = [line for line in evidence_lines if line]
        if not evidence_lines:
            evidence_lines = [message]

        signature = sha1_text(f"{stage}:{error_type}:{root_label}:{message}")[:12]
        return IssueFingerprint(
            issueId=f"ISSUE_900_{signature}",
            stage=stage,
            errorType=error_type,
            rootCauseLabel=root_label,
            normalizedMessage=message,
            signature=signature,
            confidence=confidence,
            evidenceLines=evidence_lines[:6],
        )

    def run(self, render_report: dict) -> dict:
        stderr_path = Path(render_report["stderr_path"])
        stdout_path = Path(render_report["stdout_path"])
        stderr = stderr_path.read_text(encoding="utf-8", errors="ignore") if stderr_path.exists() else ""
        stdout = stdout_path.read_text(encoding="utf-8", errors="ignore") if stdout_path.exists() else ""
        text = "\n".join([stdout, stderr])

        issues: list[IssueFingerprint] = []
        
        # 第一层：正则匹配（仅 100% 确定的 Python 标准错误）
        regex_matched = False
        for idx, (pattern, stage, err_type, root_label) in enumerate(self.COMMON_PATTERNS, start=1):
            match = pattern.search(text)
            if match:
                regex_matched = True
                msg = match.groupdict().get("msg", pattern.pattern)
                signature = sha1_text(f"{stage}:{err_type}:{root_label}:{msg.strip()}")[:12]
                issues.append(
                    IssueFingerprint(
                        issueId=f"ISSUE_{idx:03d}_{signature}",
                        stage=stage,
                        errorType=err_type,
                        rootCauseLabel=root_label,
                        normalizedMessage=msg.strip(),
                        signature=signature,
                        confidence=0.95,  # 正则匹配的置信度很高
                        evidenceLines=[msg.strip()],
                    )
                )
                logger.info(
                    "[diagnoser] regex matched: %s (confidence=0.95)",
                    root_label
                )
                break  # 找到第一个匹配就停止（避免多个规则匹配同一错误）

        # 第二层：如果正则未匹配，且启用了 LLM，使用 LLM 诊断
        if not issues and not render_report.get("success"):
            if self.enable_llm_fallback and self.llm_client:
                logger.info("[diagnoser] regex failed, trying LLM diagnosis...")
                llm_issue = self._try_llm_diagnose(
                    stderr=stderr,
                    stdout=stdout,
                    exit_code=render_report.get("exit_code"),
                )
                if llm_issue:
                    issues.append(llm_issue)
                    logger.info(
                        "[diagnoser] LLM diagnosed: %s (confidence=%.2f)",
                        llm_issue.root_cause_label,
                        llm_issue.confidence
                    )
                else:
                    logger.warning("[diagnoser] LLM diagnosis failed or returned invalid result")
            else:
                logger.warning(
                    "[diagnoser] LLM fallback disabled or client not available, "
                    "will use generic failure message"
                )

        # 第三层：如果仍然没有诊断结果，返回通用失败
        if not issues and not render_report.get("success"):
            msg = f"Render failed with exit code {render_report.get('exit_code')}"
            signature = sha1_text(msg)[:12]
            issues.append(
                IssueFingerprint(
                    issueId=f"ISSUE_999_{signature}",
                    stage="render",
                    errorType="RenderFailure",
                    rootCauseLabel="generic_render_failure",
                    normalizedMessage=msg,
                    signature=signature,
                    confidence=0.5,  # 通用失败的置信度较低
                    evidenceLines=[msg],
                )
            )
            logger.info("[diagnoser] using generic failure message (confidence=0.5)")

        return {"issues": [issue.model_dump(by_alias=True) for issue in issues]}
