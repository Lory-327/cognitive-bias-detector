import json
import re
import os
import sys
from pathlib import Path
from typing import Generator, Dict, List, Optional

PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

def load_env_file(env_path: Path) -> None:
    if not env_path.exists():
        return
    with open(env_path, 'r', encoding='utf-8') as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith('#') or '=' not in line:
                continue
            key, value = line.split('=', 1)
            key = key.strip()
            value = value.strip().strip('"').strip("'")
            os.environ[key] = value

load_env_file(PROJECT_ROOT / ".env")

from debate.llm_client import LLMClient
from debate.state_machine import DebateStateMachine, DebateState

try:
    from core.bias_detector import BiasDetector
    UPSTREAM_READY = True
except ImportError:
    UPSTREAM_READY = False
    print("⚠️ 上游模块未就绪，使用Mock数据")

MOCK_DEBATE_FOCUS = {
    "primary_target": "沉没成本谬误",
    "primary_confidence": 0.85,
    "key_questions": [
        "你已经投入了多少钱？",
        "这些投入还能收回吗？",
        "如果从头开始，你还会做这个决策吗？"
    ],
    "defense_angles": [
        "继续投入有机会翻盘，放弃则确定损失",
        "已投入的资金是历史成本，不应影响未来决策"
    ],
    "judge_criteria": [
        "投入是否可收回",
        "未来收益是否独立于过去投入",
        "情绪影响程度"
    ]
}


class DebateOrchestrator:
    """三角色AI辩论编排器 - 每个角色使用不同AI"""

    # 角色 -> AI 提供商映射
    ROLE_PROVIDERS = {
        "advocate": "qwen",  # 正方：阿里云百炼
        "skeptic": "deepseek",  # 反方：DeepSeek
        "judge": "doubao"  # 评委：字节跳动
    }

    def __init__(self, use_mock: bool = False):
        # 初始化三个不同的AI客户端
        self.llm_clients = {}
        for role, provider in self.ROLE_PROVIDERS.items():
            try:
                self.llm_clients[role] = LLMClient(
                    provider=provider,
                    use_mock=use_mock
                )
                print(f"✅ {role} -> {provider}")
            except Exception as e:
                print(f"⚠️ {role} ({provider}) 初始化失败: {e}")
                # 降级到Mock
                self.llm_clients[role] = LLMClient(
                    provider="qwen",
                    use_mock=True
                )

        self.state_machine: Optional[DebateStateMachine] = None
        self.debate_focus: Optional[Dict] = None
        self.user_input: Optional[str] = None
        self.detection_result: Optional[Dict] = None
        self.prompts = self._load_prompts()
        self._cache: Dict[str, List[Dict]] = {}

    def _load_prompts(self) -> Dict[str, str]:
        prompts = {}
        prompts_dir = os.path.join(os.path.dirname(__file__), "prompts")
        for role in ["advocate", "skeptic", "judge"]:
            file_path = os.path.join(prompts_dir, f"{role}.txt")
            try:
                with open(file_path, "r", encoding="utf-8") as f:
                    prompts[role] = f.read()
            except FileNotFoundError:
                prompts[role] = f"【{role}未找到】"
        return prompts

    def _get_detection_result(self, user_input: str) -> Dict:
        if UPSTREAM_READY:
            try:
                detector = BiasDetector()
                return detector.detect(user_input)
            except Exception as e:
                print(f"⚠️ 检测失败: {e}")
                return {"debate_focus": MOCK_DEBATE_FOCUS}
        else:
            return {"debate_focus": MOCK_DEBATE_FOCUS}

    def _format_focus_for_prompt(self, focus: Dict) -> str:
        if not focus:
            return "未指定辩论焦点"
        lines = [
            f"主偏差: {focus.get('primary_target', '未知')}",
            f"置信度: {focus.get('primary_confidence', 0)}",
            "\n关键追问:",
        ]
        for q in focus.get('key_questions', []):
            lines.append(f"  - {q}")
        lines.append("\n辩护角度:")
        for d in focus.get('defense_angles', []):
            lines.append(f"  - {d}")
        lines.append("\n评估标准:")
        for c in focus.get('judge_criteria', []):
            lines.append(f"  - {c}")
        return "\n".join(lines)

    def start(self, user_input: str) -> Generator[Dict, None, None]:
        self.user_input = user_input

        cache_key = hash(user_input)
        if cache_key in self._cache:
            print("📦 使用缓存数据")
            for item in self._cache[cache_key]:
                yield item
            return

        self.detection_result = self._get_detection_result(user_input)
        self.debate_focus = self.detection_result.get("debate_focus", MOCK_DEBATE_FOCUS)

        # 替换Prompt变量
        focus_str = self._format_focus_for_prompt(self.debate_focus)
        self.prompts = self._load_prompts()
        for role in self.prompts:
            self.prompts[role] = self.prompts[role].replace("{debate_focus}", focus_str)

        self.state_machine = DebateStateMachine(max_rounds=3)

        results = []
        for result in self._run_debate():
            results.append(result)
            yield result

        self._cache[cache_key] = results

    def _run_debate(self) -> Generator[Dict, None, None]:
        while not self.state_machine.is_concluded():
            state = self.state_machine.next()

            if state == DebateState.ADVOCATE_TURN:
                yield from self._advocate_speak()
            elif state == DebateState.SKEPTIC_TURN:
                yield from self._skeptic_speak()
            elif state == DebateState.JUDGE_TURN:
                yield from self._judge_evaluate()
            elif state == DebateState.WAITING_USER:
                yield {
                    "round": self.state_machine.round,
                    "status": "waiting_user",
                    "speaker": "系统",
                    "content": "💬 请回应正方或反方的观点，或提出新的想法...",
                    "judge_data": None,
                    "user_can_intervene": True
                }
                return

        if self.state_machine.is_concluded():
            yield {
                "round": self.state_machine.round,
                "status": "concluded",
                "speaker": "系统",
                "content": "🏁 辩论已结束，正在生成最终报告...",
                "judge_data": None,
                "user_can_intervene": False
            }

    def _advocate_speak(self) -> Generator[Dict, None, None]:
        """正方 - 使用 Qwen"""
        system_prompt = self.prompts["advocate"]
        user_content = self.user_input
        history = self._format_history_for_role("正方")

        content_parts = []
        # 使用正方专属的AI客户端
        for token in self.llm_clients["advocate"].chat(
            system_prompt, user_content, history, role="advocate"
        ):
            content_parts.append(token)
            yield {
                "round": self.state_machine.round,
                "status": "advocate_turn",
                "speaker": "正方",
                "content": "".join(content_parts),
                "judge_data": None,
                "user_can_intervene": False
            }

        full_content = "".join(content_parts)
        self.state_machine.add_history("正方", full_content)

    def _skeptic_speak(self) -> Generator[Dict, None, None]:
        """反方 - 使用 DeepSeek"""
        system_prompt = self.prompts["skeptic"]

        round_history = self.state_machine.get_round_history()
        advocate_msgs = [h for h in round_history if h["speaker"] == "正方"]

        if advocate_msgs:
            user_content = advocate_msgs[-1]["content"]
        else:
            user_content = self.user_input

        history = self._format_history_for_role("反方")

        content_parts = []
        # 使用反方专属的AI客户端
        for token in self.llm_clients["skeptic"].chat(
            system_prompt, user_content, history, role="skeptic"
        ):
            content_parts.append(token)
            yield {
                "round": self.state_machine.round,
                "status": "skeptic_turn",
                "speaker": "反方",
                "content": "".join(content_parts),
                "judge_data": None,
                "user_can_intervene": False
            }

        full_content = "".join(content_parts)
        self.state_machine.add_history("反方", full_content)

    def _judge_evaluate(self) -> Generator[Dict, None, None]:
        """评委 - 使用 SiliconFlow"""
        system_prompt = self.prompts["judge"]

        round_history = self.state_machine.get_round_history()
        history_text = "\n\n".join([
            f"【{h['speaker']}】{h['content']}"
            for h in round_history
        ])

        user_content = f"请基于以下本轮辩论内容给出评估：\n\n{history_text}"

        content_parts = []
        # 使用评委专属的AI客户端
        for token in self.llm_clients["judge"].chat(
            system_prompt, user_content, role="judge"
        ):
            content_parts.append(token)
            yield {
                "round": self.state_machine.round,
                "status": "judge_turn",
                "speaker": "评委",
                "content": "".join(content_parts),
                "judge_data": None,
                "user_can_intervene": False
            }

        full_content = "".join(content_parts)
        self.state_machine.add_history("评委", full_content)

        judge_data = self._parse_judge_json(full_content)

        if judge_data and judge_data.get("debate_status") == "concluded":
            self.state_machine.force_conclude()

        yield {
            "round": self.state_machine.round,
            "status": "judge_turn",
            "speaker": "评委",
            "content": full_content,
            "judge_data": judge_data,
            "user_can_intervene": False
        }

    def _parse_judge_json(self, content: str) -> Optional[Dict]:
        try:
            return json.loads(content)
        except json.JSONDecodeError:
            pass

        json_pattern = r'\{[\s\S]*?\}'
        matches = re.findall(json_pattern, content)

        for match in matches:
            try:
                return json.loads(match)
            except json.JSONDecodeError:
                continue

        print("⚠️ 评委JSON解析失败，使用回退策略")
        return {
            "round": self.state_machine.round if self.state_machine else 1,
            "primary_bias": self.debate_focus.get("primary_target", "未知") if self.debate_focus else "未知",
            "debate_status": "continuing",
            "next_focus": "继续探讨",
            "suggestion": "请继续辩论以获取更多信息",
            "evaluation": {
                "bias_probability": 50,
                "impact_level": "中",
                "confidence": 0.5
            }
        }

    def _format_history_for_role(self, current_role: str) -> List[Dict]:
        history = []
        for h in self.state_machine.history:
            if h["speaker"] == "用户":
                role = "user"
            elif h["speaker"] == current_role:
                role = "assistant"
            else:
                role = "user"

            history.append({
                "role": role,
                "content": f"【{h['speaker']}】{h['content']}"
            })
        return history

    def user_reply(self, reply_text: str) -> Generator[Dict, None, None]:
        self.state_machine.add_history("用户", reply_text)
        yield from self._run_debate()

    def generate_report(self) -> Dict:
        if not self.state_machine:
            return {"error": "辩论尚未开始"}

        primary_from_detection = {}
        if self.detection_result and "primary_bias" in self.detection_result:
            pb = self.detection_result["primary_bias"]
            primary_from_detection = {
                "bias_name": pb.get("bias_name", "未知"),
                "confidence": pb.get("confidence", 0)
            }

        judge_history = [
            h for h in self.state_machine.get_all_history()
            if h["speaker"] == "评委"
        ]

        judge_evaluations = []
        for h in judge_history:
            data = self._parse_judge_json(h["content"])
            if data:
                judge_evaluations.append(data)

        primary_bias = primary_from_detection
        if not primary_bias and judge_evaluations:
            last_eval = judge_evaluations[-1]
            primary_bias = {
                "bias_name": last_eval.get("primary_bias", "未知"),
                "confidence": last_eval.get("evaluation", {}).get("confidence", 0)
            }
        elif not primary_bias and self.debate_focus:
            primary_bias = {
                "bias_name": self.debate_focus.get("primary_target", "未知"),
                "confidence": self.debate_focus.get("primary_confidence", 0)
            }

        risk_level = self._calculate_risk_level(judge_evaluations)

        final_suggestion = "无建议"
        if judge_evaluations:
            final_suggestion = judge_evaluations[-1].get("suggestion", "无建议")

        report = {
            "debate_rounds": self.state_machine.round,
            "primary_bias": primary_bias,
            "secondary_biases": self.detection_result.get("secondary_biases", []) if self.detection_result else [],
            "judge_history": judge_evaluations,
            "final_suggestion": final_suggestion,
            "risk_level": risk_level,
            "ai_providers": self.ROLE_PROVIDERS  # 记录使用的AI提供商
        }

        if self.detection_result:
            report["input_analysis"] = self.detection_result.get("input_analysis", {})
            report["detected_biases"] = self.detection_result.get("detected_biases", [])

        return report

    def _calculate_risk_level(self, evaluations: List[Dict]) -> str:
        if not evaluations:
            return self.detection_result.get("risk_level", "低") if self.detection_result else "低"

        probabilities = []
        for e in evaluations:
            prob = e.get("evaluation", {}).get("bias_probability", 0)
            probabilities.append(prob)

        avg_probability = sum(probabilities) / len(probabilities)

        if avg_probability >= 80:
            return "高"
        elif avg_probability >= 50:
            return "中"
        else:
            return "低"


if __name__ == "__main__":
    print("=" * 60)
    print("🧪 三AI辩论系统测试")
    print("=" * 60)

    orch = DebateOrchestrator(use_mock=True)

    print(f"\nAI配置:")
    for role, provider in orch.ROLE_PROVIDERS.items():
        print(f"  {role}: {provider}")

    print("\n🚀 启动辩论...")
    print("=" * 60)

    for r in orch.start('我已经投了这么多钱，必须坚持'):
        if r['status'] in ['advocate_turn', 'skeptic_turn', 'judge_turn']:
            content = r['content']
            if len(content) > 20 and content[-1] in '。！？.!?':
                print(f'\n[{r["speaker"]}] {content}')
                if r['judge_data']:
                    print(f'  📊 {json.dumps(r["judge_data"], ensure_ascii=False)}')

        elif r['status'] == 'waiting_user':
            print(f'\n[{r["speaker"]}] {r["content"]}')
            break

    print('\n' + '=' * 60)
    print('💬 用户回复: 但是继续投入可能损失更多')
    print('=' * 60)

    for r in orch.user_reply('但是继续投入可能损失更多'):
        if r['status'] in ['advocate_turn', 'skeptic_turn', 'judge_turn']:
            content = r['content']
            if len(content) > 20 and content[-1] in '。！？.!?':
                print(f'\n[{r["speaker"]}] {content}')
                if r['judge_data']:
                    print(f'  📊 {json.dumps(r["judge_data"], ensure_ascii=False)}')

    print('\n' + '=' * 60)
    print('📊 最终报告')
    print('=' * 60)
    report = orch.generate_report()
    print(json.dumps(report, ensure_ascii=False, indent=2))
