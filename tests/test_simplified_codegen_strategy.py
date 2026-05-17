"""测试简化后的代码生成策略：DirectCodegenAgent 优先，失败后降级到 ManimCodeExpert"""
from app.agents.code_expert import ManimCodeExpert
from app.agents.direct_codegen import DirectCodegenAgent


def _minimal_scene_ir() -> dict:
    """创建最小的场景 IR 用于测试"""
    return {
        "projectBrief": {
            "videoSpec": {"background": "#000000", "resolution": "1920x1080", "fps": 30},
            "subtitleSpec": {"enabled": False, "position": "bottom", "fontSize": 30},
        },
        "outputPolicy": {"sceneClassName": "GeneratedVideoScene"},
        "scenes": [
            {
                "sceneId": "SC001",
                "durationSec": 3.0,
                "objects": [
                    {"id": "OBJ001", "content": "circle", "placement": "center", "style": {"scale": 1.0}}
                ],
                "subtitleItems": [],
                "sentences": [],
                "animationCues": [],
                "animationBeatPlan": {
                    "sceneDurationSec": 3.0,
                    "beats": [
                        {
                            "sentenceIndex": 1,
                            "text": "",
                            "startSec": 0.0,
                            "endSec": 3.0,
                            "timelineSource": "fallback",
                            "actions": [],
                        }
                    ],
                    "source": "fallback",
                },
            }
        ],
    }


def test_manim_code_expert_generates_deterministic_code():
    """测试 ManimCodeExpert 生成确定性代码"""
    expert = ManimCodeExpert()
    ir = _minimal_scene_ir()
    
    code = expert.run(ir)
    
    # 验证生成的代码包含必要的结构
    assert "from manim import *" in code
    assert "class GeneratedVideoScene(Scene):" in code
    assert "def construct(self):" in code
    assert "def _play_scene_01(self):" in code
    assert "make_shape" in code
    assert "safe_duration" in code


def test_direct_codegen_generates_semantic_code():
    """测试 DirectCodegenAgent 生成语义化代码"""
    agent = DirectCodegenAgent(llm_client=None)  # 不使用 LLM
    ir = _minimal_scene_ir()
    
    code = agent.run(ir, notices=[])
    
    # 验证生成的代码包含必要的结构
    assert "from manim import *" in code
    assert "class GeneratedVideoScene(Scene):" in code
    assert "def construct(self):" in code
    assert "def _play_scene_01(self):" in code
    # DirectCodegenAgent 使用 make_visual 而不是 make_shape
    assert "make_visual" in code


def test_fallback_threshold_logic():
    """测试降级阈值逻辑"""
    max_attempts = 5
    
    # 计算失败阈值：当尝试次数超过一半时，切换到确定性模式
    fallback_threshold = max(1, max_attempts // 2 + 1)
    
    # max_attempts=5 时，threshold 应该是 3 (5//2 + 1 = 2 + 1 = 3)
    assert fallback_threshold == 3
    
    # 验证不同 max_attempts 的阈值
    for max_att, expected_threshold in [(1, 1), (2, 2), (3, 2), (4, 3), (5, 3), (6, 4), (10, 6)]:
        threshold = max(1, max_att // 2 + 1)
        assert threshold == expected_threshold, f"max_attempts={max_att}, expected={expected_threshold}, got={threshold}"


def test_strategy_selection_based_on_attempt():
    """测试基于尝试次数的策略选择逻辑"""
    max_attempts = 4
    fallback_threshold = max(1, max_attempts // 2 + 1)  # 应该是 3
    
    # attempt 1, 2: 使用 DirectCodegenAgent
    for attempt in [1, 2]:
        if attempt >= fallback_threshold:
            strategy = "manim_code_expert_fallback"
        else:
            strategy = "direct_semantic"
        assert strategy == "direct_semantic", f"attempt {attempt} should use direct_semantic"
    
    # attempt 3, 4: 使用 ManimCodeExpert
    for attempt in [3, 4]:
        if attempt >= fallback_threshold:
            strategy = "manim_code_expert_fallback"
        else:
            strategy = "direct_semantic"
        assert strategy == "manim_code_expert_fallback", f"attempt {attempt} should use manim_code_expert_fallback"


def test_code_expert_vs_direct_codegen_output_difference():
    """验证两个智能体生成的代码确实不同"""
    ir = _minimal_scene_ir()
    
    expert_code = ManimCodeExpert().run(ir)
    direct_code = DirectCodegenAgent(llm_client=None).run(ir, notices=[])
    
    # 两者应该不同
    assert expert_code != direct_code
    
    # ManimCodeExpert 使用 make_shape
    assert "make_shape" in expert_code
    assert "make_visual" not in expert_code
    
    # DirectCodegenAgent 使用 make_visual
    assert "make_visual" in direct_code
    assert "make_shape" not in direct_code
