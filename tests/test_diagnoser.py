from pathlib import Path

from app.agents.diagnoser import ErrorDiagnoser
from app.llm.base import BaseLLMClient


class _LLMStub(BaseLLMClient):
    def __init__(self, response: str) -> None:
        self.response = response
        self.calls = 0

    def complete(self, system_prompt: str, user_prompt: str) -> str:
        self.calls += 1
        return self.response


class _FailIfCalledLLM(BaseLLMClient):
    def complete(self, system_prompt: str, user_prompt: str) -> str:
        raise AssertionError("LLM should not be called when regex already matches")


def _write_logs(tmp_path: Path, stdout: str, stderr: str) -> tuple[str, str]:
    stdout_path = tmp_path / "stdout.log"
    stderr_path = tmp_path / "stderr.log"
    stdout_path.write_text(stdout, encoding="utf-8")
    stderr_path.write_text(stderr, encoding="utf-8")
    return str(stdout_path), str(stderr_path)


def test_diagnoser_regex_hit_skips_llm(tmp_path: Path) -> None:
    stdout_path, stderr_path = _write_logs(
        tmp_path,
        stdout="",
        stderr="NameError: name 'WHITE' is not defined",
    )
    diagnoser = ErrorDiagnoser(llm_client=_FailIfCalledLLM(), enable_llm_fallback=True)

    result = diagnoser.run(
        {
            "success": False,
            "exit_code": 1,
            "stdout_path": stdout_path,
            "stderr_path": stderr_path,
        }
    )

    assert result["issues"][0]["rootCauseLabel"] == "undefined_name"


def test_diagnoser_uses_llm_when_regex_misses(tmp_path: Path) -> None:
    stdout_path, stderr_path = _write_logs(
        tmp_path,
        stdout="",
        stderr="TypeError: Animation only works on Mobjects",
    )
    llm = _LLMStub(
        '{"stage":"runtime","errorType":"TypeError","rootCauseLabel":"animation_target_not_mobject",'
        '"normalizedMessage":"Animation only works on Mobjects","confidence":0.94,'
        '"evidenceLines":["TypeError: Animation only works on Mobjects"]}'
    )
    diagnoser = ErrorDiagnoser(llm_client=llm, enable_llm_fallback=True)

    result = diagnoser.run(
        {
            "success": False,
            "exit_code": 1,
            "stdout_path": stdout_path,
            "stderr_path": stderr_path,
        }
    )

    assert llm.calls == 1
    issue = result["issues"][0]
    assert issue["issueId"].startswith("ISSUE_900_")
    assert issue["rootCauseLabel"] == "animation_target_not_mobject"
    assert issue["errorType"] == "TypeError"


def test_diagnoser_falls_back_when_llm_output_invalid(tmp_path: Path) -> None:
    stdout_path, stderr_path = _write_logs(
        tmp_path,
        stdout="",
        stderr="TypeError: Animation only works on Mobjects",
    )
    llm = _LLMStub("not-json")
    diagnoser = ErrorDiagnoser(llm_client=llm, enable_llm_fallback=True)

    result = diagnoser.run(
        {
            "success": False,
            "exit_code": 1,
            "stdout_path": stdout_path,
            "stderr_path": stderr_path,
        }
    )

    assert llm.calls == 1
    issue = result["issues"][0]
    assert issue["rootCauseLabel"] == "generic_render_failure"
    assert issue["issueId"].startswith("ISSUE_999_")


def test_diagnoser_keeps_legacy_fallback_when_llm_disabled(tmp_path: Path) -> None:
    stdout_path, stderr_path = _write_logs(
        tmp_path,
        stdout="",
        stderr="TypeError: Animation only works on Mobjects",
    )
    diagnoser = ErrorDiagnoser(enable_llm_fallback=False)

    result = diagnoser.run(
        {
            "success": False,
            "exit_code": 1,
            "stdout_path": stdout_path,
            "stderr_path": stderr_path,
        }
    )

    issue = result["issues"][0]
    assert issue["rootCauseLabel"] == "generic_render_failure"
    assert issue["normalizedMessage"] == "Render failed with exit code 1"

