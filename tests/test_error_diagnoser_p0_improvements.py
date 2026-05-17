"""测试 ErrorDiagnoser 的 P0 改进 - Manim 特定错误诊断"""
import tempfile
from pathlib import Path
from app.agents.diagnoser import ErrorDiagnoser


def create_temp_log(error_message: str) -> tuple[Path, Path]:
    """创建临时日志文件用于测试"""
    stderr_file = Path(tempfile.mktemp(suffix=".log"))
    stdout_file = Path(tempfile.mktemp(suffix=".log"))
    
    stderr_file.write_text(error_message, encoding="utf-8")
    stdout_file.write_text("", encoding="utf-8")
    
    return stderr_file, stdout_file


def test_diagnose_animate_non_mobject():
    """测试诊断 animate_non_mobject 错误"""
    diagnoser = ErrorDiagnoser()
    
    error_msg = "ManimError: Cannot animate non-mobject objects.\nMake sure all arguments to Play are animations."
    stderr_file, stdout_file = create_temp_log(error_msg)
    
    report = {
        "success": False,
        "stderr_path": str(stderr_file),
        "stdout_path": str(stdout_file),
        "exit_code": 1
    }
    
    result = diagnoser.run(report)
    
    assert len(result["issues"]) > 0
    issue = result["issues"][0]
    assert issue["rootCauseLabel"] == "animate_non_mobject"
    assert issue["errorType"] == "ManimError"
    
    # 清理
    stderr_file.unlink()
    stdout_file.unlink()


def test_diagnose_latex_compilation_failed():
    """测试诊断 LaTeX 编译失败"""
    diagnoser = ErrorDiagnoser()
    
    error_msg = "RuntimeError: latex failed but you might not see the failure message.\nCheck your LaTeX installation."
    stderr_file, stdout_file = create_temp_log(error_msg)
    
    report = {
        "success": False,
        "stderr_path": str(stderr_file),
        "stdout_path": str(stdout_file),
        "exit_code": 1
    }
    
    result = diagnoser.run(report)
    
    assert len(result["issues"]) > 0
    issue = result["issues"][0]
    assert issue["rootCauseLabel"] == "latex_compilation_failed"
    assert issue["errorType"] == "LatexError"
    
    # 清理
    stderr_file.unlink()
    stdout_file.unlink()


def test_diagnose_incompatible_mobject_transform():
    """测试诊断不兼容的 Mobject 变换"""
    diagnoser = ErrorDiagnoser()
    
    error_msg = "ValueError: Cannot interpolate between different types of mobjects"
    stderr_file, stdout_file = create_temp_log(error_msg)
    
    report = {
        "success": False,
        "stderr_path": str(stderr_file),
        "stdout_path": str(stdout_file),
        "exit_code": 1
    }
    
    result = diagnoser.run(report)
    
    assert len(result["issues"]) > 0
    issue = result["issues"][0]
    assert issue["rootCauseLabel"] == "incompatible_mobject_transform"
    assert issue["errorType"] == "ManimError"
    
    # 清理
    stderr_file.unlink()
    stdout_file.unlink()


def test_diagnose_missing_key_reference():
    """测试诊断缺失的对象引用"""
    diagnoser = ErrorDiagnoser()
    
    error_msg = "KeyError: 'OBJ999'"
    stderr_file, stdout_file = create_temp_log(error_msg)
    
    report = {
        "success": False,
        "stderr_path": str(stderr_file),
        "stdout_path": str(stdout_file),
        "exit_code": 1
    }
    
    result = diagnoser.run(report)
    
    assert len(result["issues"]) > 0
    issue = result["issues"][0]
    assert issue["rootCauseLabel"] == "missing_key_reference"
    assert issue["errorType"] == "KeyError"
    
    # 清理
    stderr_file.unlink()
    stdout_file.unlink()


def test_diagnose_index_out_of_range():
    """测试诊断索引越界"""
    diagnoser = ErrorDiagnoser()
    
    error_msg = "IndexError: list index out of range"
    stderr_file, stdout_file = create_temp_log(error_msg)
    
    report = {
        "success": False,
        "stderr_path": str(stderr_file),
        "stdout_path": str(stdout_file),
        "exit_code": 1
    }
    
    result = diagnoser.run(report)
    
    assert len(result["issues"]) > 0
    issue = result["issues"][0]
    assert issue["rootCauseLabel"] == "index_out_of_range"
    assert issue["errorType"] == "IndexError"
    
    # 清理
    stderr_file.unlink()
    stdout_file.unlink()


def test_diagnose_improved_run_time_error():
    """测试改进后的 run_time 错误诊断"""
    diagnoser = ErrorDiagnoser()
    
    # 测试多种 run_time 错误消息变体
    test_cases = [
        "ValueError: run_time must be positive",
        "ValueError: run_time <= 0 is not allowed",
        "ValueError: Animation run_time cannot be negative",
    ]
    
    for error_msg in test_cases:
        stderr_file, stdout_file = create_temp_log(error_msg)
        
        report = {
            "success": False,
            "stderr_path": str(stderr_file),
            "stdout_path": str(stdout_file),
            "exit_code": 1
        }
        
        result = diagnoser.run(report)
        
        assert len(result["issues"]) > 0, f"Failed to diagnose: {error_msg}"
        issue = result["issues"][0]
        assert issue["rootCauseLabel"] == "invalid_run_time", f"Wrong label for: {error_msg}"
        
        # 清理
        stderr_file.unlink()
        stdout_file.unlink()


def test_diagnose_improved_ffmpeg_error():
    """测试改进后的 FFmpeg 错误诊断"""
    diagnoser = ErrorDiagnoser()
    
    test_cases = [
        "ffmpeg: command not found",
        "PermissionError: [Errno 13] Permission denied: 'ffmpeg'",
        "subprocess.CalledProcessError: Command '['ffmpeg', ...]' returned non-zero exit status 1",
    ]
    
    for error_msg in test_cases:
        stderr_file, stdout_file = create_temp_log(error_msg)
        
        report = {
            "success": False,
            "stderr_path": str(stderr_file),
            "stdout_path": str(stdout_file),
            "exit_code": 1
        }
        
        result = diagnoser.run(report)
        
        assert len(result["issues"]) > 0, f"Failed to diagnose: {error_msg}"
        issue = result["issues"][0]
        assert issue["rootCauseLabel"] == "ffmpeg_related", f"Wrong label for: {error_msg}"
        
        # 清理
        stderr_file.unlink()
        stdout_file.unlink()


def test_diagnose_memory_and_disk_errors():
    """测试内存和磁盘错误诊断"""
    diagnoser = ErrorDiagnoser()
    
    test_cases = [
        ("MemoryError: Unable to allocate array", "insufficient_memory"),
        ("OSError: [Errno 28] No space left on device", "disk_full"),
    ]
    
    for error_msg, expected_label in test_cases:
        stderr_file, stdout_file = create_temp_log(error_msg)
        
        report = {
            "success": False,
            "stderr_path": str(stderr_file),
            "stdout_path": str(stdout_file),
            "exit_code": 1
        }
        
        result = diagnoser.run(report)
        
        assert len(result["issues"]) > 0, f"Failed to diagnose: {error_msg}"
        issue = result["issues"][0]
        assert issue["rootCauseLabel"] == expected_label, f"Wrong label for: {error_msg}"
        
        # 清理
        stderr_file.unlink()
        stdout_file.unlink()


def test_coverage_summary():
    """测试覆盖率总结"""
    diagnoser = ErrorDiagnoser()
    
    # 统计所有支持的错误类型
    supported_labels = set()
    for pattern, stage, err_type, root_label in diagnoser.COMMON_PATTERNS:
        supported_labels.add(root_label)
    
    print(f"\n{'='*60}")
    print(f"ErrorDiagnoser 当前支持的错误类型总数: {len(supported_labels)}")
    print(f"{'='*60}")
    
    # 按类别分组
    categories = {
        "Python 标准错误": ["python_syntax_error", "missing_import", "missing_module", 
                          "undefined_name", "bad_attribute_access", "value_error", 
                          "missing_file"],
        "Manim 特定错误": ["animate_non_mobject", "incompatible_mobject_transform", 
                          "manim_runtime_error", "invalid_keyword_in_mobject_initialization"],
        "LaTeX 错误": ["latex_compilation_failed"],
        "索引和引用": ["index_out_of_range", "missing_key_reference"],
        "运行时错误": ["invalid_run_time"],
        "环境错误": ["ffmpeg_related", "insufficient_memory", "disk_full"],
    }
    
    for category, labels in categories.items():
        covered = [label for label in labels if label in supported_labels]
        print(f"\n{category}: {len(covered)}/{len(labels)}")
        for label in covered:
            print(f"  ✓ {label}")
        missing = [label for label in labels if label not in supported_labels]
        for label in missing:
            print(f"  ✗ {label} (未覆盖)")
    
    print(f"\n{'='*60}\n")
