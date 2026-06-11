# 模块间接口文档

## 模块A → 模块C：认知偏差知识库

**提供者**：崔庆芳 (`data/bias_knowledge_base.py`)
**使用者**：韩琴 (`core/bias_detector.py`)

### 暴露接口
```python
BIAS_DATABASE = {偏差名: BiasInfo}
CROSSOVER_ADJUSTMENT = {(偏差A, 偏差B): Adjustment}

def get_bias_info(bias_id: str) -> dict
def get_crossover_adjustment(bias_a: str, bias_b: str) -> dict
def get_biases_by_category(category: str) -> list
BiasInfo 结构
Python
{
    "id": str,                    # 英文ID，如 "sunk_cost"
    "category": str,              # 投入类/信息类/情绪类/社会类/推理类/自我类
    "description": str,           # 偏差描述
    "trigger_keywords": list,     # 触发关键词列表（>=8个）
    "core_rules": list,          # 核心判定规则（3条）
    "distinguish_features": dict,  # 与其他偏差的区分特征
    "base_weight": float,        # 基础权重（0.5-1.0）
    "crossover_with": list,      # 常见交叉偏差列表
    "examples": list             # 示例语句（2个）
}
模块B → 模块C：输入解析引擎
提供者：杨惠蓝 (core/input_parser.py)
使用者：韩琴 (core/bias_detector.py)
暴露接口
Python
class InputParser:
    def extract(self, text: str) -> ParsedResult
ParsedResult 结构
Python
{
    "original_text": str,
    "decision_type": str,         # 购房置业/投资理财/职业发展/消费购物/未分类
    "key_elements": {
        "decision_target": str or None,
        "stated_reason": list,
        "numbers": list
    },
    "implied_assumptions": list,    # 字符串列表，如 ["past_equals_future"]
    "emotion_tags": list,         # 字符串列表，如 ["hesitation", "anxiety"]
    "cost_signals": list,         # 字符串列表，如 ["time_cost", "money_cost"]
    "time_pressure": {
        "has_pressure": bool,
        "pressure_level": str,    # 高/中/低/无
        "keywords": list
    },
    "alternatives": {
        "considered_alternatives": bool,
        "explicitly_rejected_alternatives": bool,
        "evidence": list
    }
}
模块C → 模块D：偏差识别引擎
提供者：韩琴 (core/bias_detector.py)
使用者：罗晓玲 (debate/debate_orchestrator.py)
暴露接口
Python
class BiasDetector:
    def detect(self, text: str) -> DetectionResult
DetectionResult 结构
Python
{
    "input_analysis": ParsedResult,    # 来自模块B的解析结果
    "detected_biases": list,          # 所有检测到的偏差
    "primary_bias": {                 # 主偏差（可能为None）
        "bias_name": str,
        "bias_id": str,
        "category": str,
        "confidence": float,          # 0-0.98
        "evidence": list,
        "matched_rules": list,
        "crossover_note": str,        # 可选
        "ambiguity_warning": str      # 可选
    },
    "secondary_biases": list,         # 次要偏差列表
    "debate_focus": {                 # 辩论焦点
        "primary_target": str,
        "primary_confidence": float,
        "key_questions": list,        # 反方追问（3-4个）
        "defense_angles": list,       # 正方辩护（2个）
        "judge_criteria": list        # 评委评估标准（3个）
    },
    "risk_level": str                 # 高/中/低
}
模块D → 组长：辩论编排器
提供者：罗晓玲 (debate/debate_orchestrator.py)
使用者：组长 (main.py, app_gradio.py)
暴露接口
Python
class DebateOrchestrator:
    def start(self, user_input: str) -> Generator[dict, None, None]
    def user_reply(self, reply_text: str) -> Generator[dict, None, None]
    def generate_report(self) -> dict
每轮 yield 结构
Python
{
    "round": int,
    "status": str,                    # advocate_turn/skeptic_turn/judge_turn/waiting_user/concluded
    "speaker": str,                   # 正方/反方/评委
    "content": str,                 # AI发言内容
    "judge_data": dict or None,       # 评委JSON判定（仅评委轮）
    "user_can_intervene": bool
}
最终报告结构
Python
{
    "debate_rounds": int,
    "primary_bias": dict,
    "secondary_biases": list,
    "judge_history": list,
    "final_suggestion": str,
    "risk_level": str
}
调用示例
Python
# 完整流程示例
from core.input_parser import InputParser
from core.bias_detector import BiasDetector
from debate.debate_orchestrator import DebateOrchestrator

# 1. 解析输入
parser = InputParser()
parsed = parser.extract("我已经投了这么多钱，必须坚持")

# 2. 识别偏差
detector = BiasDetector()
result = detector.detect("我已经投了这么多钱，必须坚持")

# 3. 启动辩论
orchestrator = DebateOrchestrator()
for event in orchestrator.start("我已经投了这么多钱，必须坚持"):
    print(f"{event['speaker']}: {event['content']}")
