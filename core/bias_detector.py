import sys
import os

# 将项目根目录添加到Python路径
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass, field

# 导入知识库
from data.bias_knowledge_base import BIAS_DATABASE, CROSSOVER_ADJUSTMENT

# 导入解析器
from core.input_parser import InputParser, ParserOutputContract


@dataclass
class BiasScore:
    # 偏差评分数据结构
    bias_name: str
    bias_id: str
    category: str
    confidence: float
    evidence: List[str] = field(default_factory=list)
    matched_keywords: List[str] = field(default_factory=list)
    assumption_code: str = ""


class BiasDetector:
    # 偏差识别引擎

    def __init__(self):
        self.parser = InputParser()
        self.bias_database = BIAS_DATABASE
        self.crossover_rules = CROSSOVER_ADJUSTMENT

        # 假设代码到偏差名称的映射
        self.assumption_bias_map = {
            "sunk_cost_continuation": ["沉没成本谬误", "承诺升级", "损失厌恶"],
            "past_equals_future": ["线性外推", "可得性偏差", "过度自信"],
            "peer_experience_equals_my_result": ["从众心理", "可得性偏差", "幸存者偏差"],
            "information_equals_accuracy": ["确认偏误", "过度自信", "信息茧房"],
            "scarcity_requires_action": ["稀缺性偏误", "行动偏见", "损失厌恶"]
        }

        # 偏差优先级（数字越小优先级越高）
        self.bias_priority = {
            "确认偏误": 1,
            "沉没成本谬误": 2,
            "线性外推": 3,
            "损失厌恶": 4,
            "可得性偏差": 5,
            "从众心理": 6,
            "禀赋效应": 7,
            "过度自信": 8,
            "锚定效应": 9,
            "框架效应": 10,
        }

        # 辩论焦点模板
        self.focus_map = self._init_focus_map()

    def _init_focus_map(self) -> Dict:
        # 初始化辩论焦点模板
        return {
            "沉没成本谬误": {
                "key_questions": [
                    "如果今天是你第一次做这个决策，没有之前的投入，你还会继续吗？",
                    "未来的收益预期是否真的能覆盖继续投入的成本？",
                    "有没有可能及时止损反而更明智？",
                    "你如何区分'坚持'和'浪费'的界限？"
                ],
                "defense_angles": [
                    "已有投入产生了积累效应，放弃会损失已形成的优势",
                    "项目接近完成，继续投入的边际成本低于重启新项目"
                ],
                "judge_criteria": [
                    "未来收益是否独立于过去投入？",
                    "是否有客观证据支持继续投入？"
                ]
            },
            "确认偏误": {
                "key_questions": [
                    "你有没有主动寻找过反对你观点的信息？",
                    "换一个立场，你会如何看待同样的证据？",
                    "有没有可能你忽略了关键的负面信息？"
                ],
                "defense_angles": [
                    "多角度分析后，支持性证据更充分",
                    "反对观点已经被考虑过但不够有力"
                ],
                "judge_criteria": [
                    "信息检索是否系统全面？",
                    "是否检验了关键假设？"
                ]
            },
            "可得性偏差": {
                "key_questions": [
                    "你提到的案例是否具有代表性？有没有反例？",
                    "容易想到的事件是否真的更可能发生？",
                    "你的判断是来自统计数据还是个人经历？"
                ],
                "defense_angles": [
                    "个人经历和身边案例是最可靠的信息来源"
                ],
                "judge_criteria": [
                    "证据来源是否多样且平衡？",
                    "是否考虑了基础概率？"
                ]
            },
            "线性外推": {
                "key_questions": [
                    "过去趋势一定会延续到未来吗？",
                    "有没有考虑过可能导致趋势逆转的因素？",
                    "短期波动被过度解读为长期趋势了吗？"
                ],
                "defense_angles": [
                    "趋势延续是最合理的预测假设"
                ],
                "judge_criteria": [
                    "预测是否考虑了可能的转折点？",
                    "是否有非线性变化的证据？"
                ]
            },
            "从众心理": {
                "key_questions": [
                    "如果身边人都没这么做，你还会做同样选择吗？",
                    "多数人的选择就一定正确吗？",
                    "你了解别人做这个选择的理由吗？"
                ],
                "defense_angles": [
                    "群体智慧：多数人的判断更可靠"
                ],
                "judge_criteria": [
                    "是否独立评估了自己的情况？",
                    "从众的理由是信息性还是规范性？"
                ]
            },
            "损失厌恶": {
                "key_questions": [
                    "你害怕损失的程度是否超过了获得同等收益的喜悦？",
                    "'不亏'的目标是否阻碍了'赚更多'的可能？",
                    "这个决策的参照点是什么？换个参照点你的判断会变吗？"
                ],
                "defense_angles": [
                    "保住已有成果比追求不确定的收益更重要"
                ],
                "judge_criteria": [
                    "是否客观评估了损失和收益的概率分布？",
                    "参照点的选择是否合理？"
                ]
            },
            "禀赋效应": {
                "key_questions": [
                    "你对这个物品/观点的估值是否因为'拥有'而提高？",
                    "如果不属于你，你还会这么看重吗？",
                    "情感价值是否被过度放大？"
                ],
                "defense_angles": [
                    "拥有确实带来了情感价值",
                    "自己的东西值得更高的评价"
                ],
                "judge_criteria": [
                    "是否区分了使用价值和情感价值？",
                    "估值是否合理？"
                ]
            }
        }

    def detect(self, text: str) -> Dict:
        # 检测用户输入中的认知偏差
        if not text or not text.strip():
            return self._empty_result()

        # 调用解析引擎
        parsed = self.parser.extract(text)
        assumptions = parsed.get("implied_assumptions", [])

        bias_scores = []

        # 基于隐含假设识别偏差
        for assumption_code in assumptions:
            if assumption_code in self.assumption_bias_map:
                for bias_name in self.assumption_bias_map[assumption_code]:
                    if bias_name in self.bias_database:
                        confidence = self._get_confidence_by_text(text, bias_name)
                        bias_scores.append(BiasScore(
                            bias_name=bias_name,
                            bias_id=self.bias_database[bias_name].get("id", bias_name),
                            category=self.bias_database[bias_name].get("category", "未分类"),
                            confidence=confidence,
                            evidence=[f"隐含假设匹配: {assumption_code}"],
                            assumption_code=assumption_code
                        ))

        # 匹配确认偏误
        confirmation_keywords = ["印证", "我就知道", "果然", "早就觉得", "不出所料", "支持我的", "反对的都是错的"]
        if any(kw in text for kw in confirmation_keywords):
            has_confirmation = any(s.bias_name == "确认偏误" for s in bias_scores)
            if not has_confirmation:
                bias_scores.append(BiasScore(
                    bias_name="确认偏误",
                    bias_id="confirmation_bias",
                    category="信息类",
                    confidence=0.70,
                    evidence=["手动匹配: 确认偏误特征词"]
                ))

        # 匹配禀赋效应
        endowment_keywords = ["一直觉得", "始终认为", "我的判断", "我相信", "我坚信"]
        if any(kw in text for kw in endowment_keywords):
            has_endowment = any(s.bias_name == "禀赋效应" for s in bias_scores)
            if not has_endowment and not any(s.bias_name == "确认偏误" for s in bias_scores):
                bias_scores.append(BiasScore(
                    bias_name="禀赋效应",
                    bias_id="endowment_effect",
                    category="决策类",
                    confidence=0.35,
                    evidence=["手动匹配: 禀赋效应特征词"]
                ))

        # 没有识别到任何偏差，使用关键词匹配
        if len(bias_scores) == 0:
            bias_scores = self._keyword_fallback(text)

        # 按置信度排序
        bias_scores.sort(key=lambda x: x.confidence, reverse=True)

        # 应用优先级调整
        bias_scores = self._apply_priority(bias_scores)

        # 选择主偏差和次要偏差
        primary = bias_scores[0] if len(bias_scores) > 0 else None
        secondaries = bias_scores[1:4] if len(bias_scores) > 1 else []

        # 计算风险等级
        risk_level = self._calculate_risk_level(primary, secondaries)

        # 生成辩论焦点
        debate_focus = self._generate_debate_focus(primary, secondaries, parsed)

        return {
            "input_analysis": parsed,
            "detected_biases": [
                {"bias_name": s.bias_name, "confidence": round(s.confidence, 3), "evidence": s.evidence}
                for s in bias_scores[:5]
            ],
            "primary_bias": self._to_dict(primary) if primary else None,
            "secondary_biases": [self._to_dict(s) for s in secondaries],
            "debate_focus": debate_focus,
            "risk_level": risk_level
        }

    def _get_confidence_by_text(self, text: str, bias_name: str) -> float:
        # 根据文本内容微调置信度
        base_confidence = 0.75

        if bias_name == "沉没成本谬误":
            if "钱" in text or "亏" in text:
                base_confidence += 0.10
            if "时间" in text or "年" in text:
                base_confidence += 0.05

        elif bias_name == "线性外推":
            if "每年" in text or "趋势" in text:
                base_confidence += 0.10

        elif bias_name == "从众心理":
            if "朋友" in text or "身边" in text:
                base_confidence += 0.10

        elif bias_name == "确认偏误":
            if "负面新闻" in text or "支持" in text:
                base_confidence += 0.10

        return min(base_confidence, 0.98)

    def _keyword_fallback(self, text: str) -> List[BiasScore]:
        # 关键词匹配
        scores = []

        # 沉没成本
        if any(kw in text for kw in ["投入", "可惜", "放弃", "白费", "已经"]):
            scores.append(BiasScore(
                bias_name="沉没成本谬误",
                bias_id="sunk_cost",
                category="投入类",
                confidence=0.50,
                evidence=["关键词兜底匹配"]
            ))

        # 线性外推
        if any(kw in text for kw in ["每年", "趋势", "未来也会", "一直涨"]):
            scores.append(BiasScore(
                bias_name="线性外推",
                bias_id="linear_extrapolation",
                category="信息类",
                confidence=0.50,
                evidence=["关键词兜底匹配"]
            ))

        # 从众心理
        if any(kw in text for kw in ["朋友", "身边", "大家都", "别人"]):
            scores.append(BiasScore(
                bias_name="从众心理",
                bias_id="bandwagon_effect",
                category="社会类",
                confidence=0.45,
                evidence=["关键词兜底匹配"]
            ))

        return scores

    def _apply_priority(self, bias_scores: List[BiasScore]) -> List[BiasScore]:
        # 应用偏差优先级调整
        if len(bias_scores) <= 1:
            return bias_scores

        # 如果前两名置信度差距小于0.15，按优先级排序
        if abs(bias_scores[0].confidence - bias_scores[1].confidence) < 0.15:
            p1 = self.bias_priority.get(bias_scores[0].bias_name, 99)
            p2 = self.bias_priority.get(bias_scores[1].bias_name, 99)
            if p1 > p2:
                bias_scores[0], bias_scores[1] = bias_scores[1], bias_scores[0]
                if len(bias_scores) > 2 and abs(bias_scores[1].confidence - bias_scores[2].confidence) < 0.15:
                    p2 = self.bias_priority.get(bias_scores[1].bias_name, 99)
                    p3 = self.bias_priority.get(bias_scores[2].bias_name, 99)
                    if p2 > p3:
                        bias_scores[1], bias_scores[2] = bias_scores[2], bias_scores[1]

        return bias_scores

    def _calculate_risk_level(self, primary: Optional[BiasScore], secondaries: List[BiasScore]) -> str:
        # 计算风险等级
        if not primary:
            return "低"

        risk_score = primary.confidence
        for sec in secondaries[:2]:
            risk_score += sec.confidence * 0.2

        if risk_score >= 0.7:
            return "高"
        elif risk_score >= 0.4:
            return "中"
        return "低"

    def _generate_debate_focus(self, primary: Optional[BiasScore], secondaries: List[BiasScore], parsed: Dict) -> Dict:
        # 生成辩论焦点
        decision_type = parsed.get("decision_type", "一般决策")

        if not primary:
            return {
                "primary_target": "无明显偏差",
                "primary_confidence": 0.0,
                "decision_context": decision_type,
                "key_questions": [
                    "请详细描述你的决策过程和考虑因素。",
                    "你是否考虑了所有重要的信息？",
                    "有没有其他可能的行动方案？"
                ],
                "defense_angles": ["基于现有信息的合理判断"],
                "judge_criteria": ["信息充分性", "逻辑一致性", "风险考量"]
            }

        # 通用模板（用于未定义的偏差）
        if primary.bias_name not in self.focus_map:
            return {
                "primary_target": primary.bias_name,
                "primary_confidence": primary.confidence,
                "decision_context": decision_type,
                "key_questions": [
                    f"这个{decision_type}决策的依据是什么？",
                    "有没有考虑过其他可能性？",
                    "如果10年后的你回看这个决策，最可能后悔的原因是什么？"
                ],
                "defense_angles": ["基于现有信息的合理判断"],
                "judge_criteria": ["信息完整性", "逻辑严谨性", "风险意识"]
            }

        template = self.focus_map[primary.bias_name]

        # 如果有次要偏差，添加到追问中
        if secondaries:
            secondary_names = [s.bias_name for s in secondaries[:2]]
            key_questions = template["key_questions"].copy()
            key_questions.append(f"注意：同时还可能存在{', '.join(secondary_names)}，需要考虑这些偏差的交互影响。")
        else:
            key_questions = template["key_questions"]

        return {
            "primary_target": primary.bias_name,
            "primary_confidence": primary.confidence,
            "decision_context": decision_type,
            "key_questions": key_questions,
            "defense_angles": template["defense_angles"],
            "judge_criteria": template["judge_criteria"]
        }

    def _empty_result(self) -> Dict:
        # 返回空结果
        return {
            "input_analysis": {},
            "detected_biases": [],
            "primary_bias": None,
            "secondary_biases": [],
            "debate_focus": {
                "primary_target": "无输入",
                "primary_confidence": 0.0,
                "key_questions": ["请输入您的决策描述"],
                "defense_angles": [],
                "judge_criteria": []
            },
            "risk_level": "低"
        }

    def _to_dict(self, score: BiasScore) -> Dict:
        # 转换为字典
        return {
            "bias_name": score.bias_name,
            "bias_id": score.bias_id,
            "category": score.category,
            "confidence": round(score.confidence, 3),
            "evidence": score.evidence
        }


# 模块自测
if __name__ == "__main__":
    detector = BiasDetector()

    test_cases = [
        ("沉没成本", "我已经在这个项目上投入了三年时间，现在放弃太可惜了，虽然市场已经变了。"),
        ("从众/可得性", "我身边好几个朋友创业都成功了，所以创业成功率应该挺高的。"),
        ("线性外推", "房价过去十年每年涨10%，所以未来十年也会每年涨10%，现在不买以后更买不起。"),
        ("确认偏误", "我一直觉得这家公司有问题，所以每次看到负面新闻都觉得印证了我的判断。"),
        ("损失厌恶", "我已经亏了100万了，必须继续投，不然就全完了。我有信心一定能翻盘。")
    ]

    print("偏差检测器测试\n")

    for i, (name, text) in enumerate(test_cases, 1):
        print(f"\n【测试用例 {i}】{name}")
        print(f"输入: {text[:50]}...")

        result = detector.detect(text)

        print(f"决策类型: {result['input_analysis'].get('decision_type', '未知')}")
        print(f"风险等级: {result['risk_level']}")

        if result['primary_bias']:
            print(f"主偏差: {result['primary_bias']['bias_name']} (置信度: {result['primary_bias']['confidence']})")
        else:
            print("主偏差: 无")

        print(f"辩论焦点: {result['debate_focus']['primary_target']}")