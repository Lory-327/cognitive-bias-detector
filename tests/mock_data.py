"""
Mock数据：用于下游模块开发时，上游模块尚未完成的情况
"""

# Mock 1: 沉没成本案例
MOCK_INPUT_1 = "我已经投了这么多钱，必须坚持做完，不然前面的钱就白花了"

MOCK_PARSED_1 = {
    "original_text": MOCK_INPUT_1,
    "decision_type": "投资",
    "key_elements": {
        "decision_target": "项目",
        "stated_reason": ["投了这么多钱", "必须坚持做完"],
        "numbers": []
    },
    "implied_assumptions": [
        {
            "assumption": "已投入的成本需要在当前决策中得到回报",
            "related_bias": "sunk_cost",
            "evidence": ["已经投了这么多钱", "前面的钱就白花了"],
            "confidence": 0.9
        }
    ],
    "emotion_tags": [
        {"emotion": "焦虑", "intensity": 0.7, "matched_words": ["白花了"]}
    ],
    "cost_signals": [
        {"cost_type": "金钱", "matched_keywords": ["投了这么多钱"], "strength": 1}
    ],
    "time_pressure": {"has_pressure": False, "pressure_level": "无", "keywords": []},
    "alternatives": {"considered_alternatives": False, "explicitly_rejected_alternatives": True, "evidence": ["必须坚持"]}
}

# Mock 2: 可得性偏差案例
MOCK_INPUT_2 = "最近房价一直在涨，我身边朋友都赚了，我觉得现在买房应该还行"

MOCK_PARSED_2 = {
    "original_text": MOCK_INPUT_2,
    "decision_type": "购房",
    "key_elements": {
        "decision_target": "房子",
        "stated_reason": ["房价一直在涨", "朋友都赚了"],
        "numbers": []
    },
    "implied_assumptions": [
        {
            "assumption": "过去趋势会延续到未来",
            "related_bias": "linear_extrapolation",
            "evidence": ["房价一直在涨"],
            "confidence": 0.85
        },
        {
            "assumption": "他人的成功经验可以复制到我身上",
            "related_bias": "survivorship_bias",
            "evidence": ["身边朋友都赚了"],
            "confidence": 0.8
        }
    ],
    "emotion_tags": [
        {"emotion": "从众", "intensity": 0.8, "matched_words": ["朋友都赚了"]}
    ],
    "cost_signals": [],
    "time_pressure": {"has_pressure": False, "pressure_level": "无", "keywords": []},
    "alternatives": {"considered_alternatives": False, "explicitly_rejected_alternatives": False, "evidence": []}
}

# Mock 3: 确认偏误案例
MOCK_INPUT_3 = "我只看看涨的分析，看跌的都是瞎说，房价肯定还会涨"

MOCK_PARSED_3 = {
    "original_text": MOCK_INPUT_3,
    "decision_type": "投资",
    "key_elements": {
        "decision_target": "房价",
        "stated_reason": ["只看涨的分析"],
        "numbers": []
    },
    "implied_assumptions": [
        {
            "assumption": "我已经掌握了充分信息，足以做出准确判断",
            "related_bias": "overconfidence",
            "evidence": ["肯定还会涨"],
            "confidence": 0.75
        }
    ],
    "emotion_tags": [
        {"emotion": "自信", "intensity": 0.9, "matched_words": ["肯定", "瞎说"]}
    ],
    "cost_signals": [],
    "time_pressure": {"has_pressure": False, "pressure_level": "无", "keywords": []},
    "alternatives": {"considered_alternatives": False, "explicitly_rejected_alternatives": True, "evidence": ["看跌的都是瞎说"]}
}


def get_mock_parsed(input_id: int):
    """获取指定ID的Mock解析结果"""
    mocks = {1: MOCK_PARSED_1, 2: MOCK_PARSED_2, 3: MOCK_PARSED_3}
    return mocks.get(input_id, MOCK_PARSED_1)


def get_mock_input(input_id: int):
    """获取指定ID的Mock用户输入"""
    inputs = {1: MOCK_INPUT_1, 2: MOCK_INPUT_2, 3: MOCK_INPUT_3}
    return inputs.get(input_id, MOCK_INPUT_1)