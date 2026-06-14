import json
import re
import os
import sys
from pathlib import Path
from typing import Generator, Dict, List, Optional

# 添加项目根目录到 Python 路径
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

# 手动加载 .env
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

# 导入本模块组件
from debate.llm_client import LLMClient
from debate.state_machine import DebateStateMachine, DebateState

# 尝试导入上游模块（韩琴的），失败则用Mock
try:
    from core.bias_detector import BiasDetector
    UPSTREAM_READY = True
except ImportError:
    UPSTREAM_READY = False
    print("⚠️ 上游模块未就绪，使用Mock数据")

# Mock数据（韩琴完成前使用）
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
    """辩论编排器 - 整合三角色AI，管理完整辩论流程"""

    def __init__(self, provider: str = "qwen", use_mock: bool = False):
        self.llm = LLMClient(provider=provider, use_mock=use_mock)
        self.state_machine: Optional[DebateStateMachine] = None
        self.debate_focus: Optional[Dict] = None
        self.user_input: Optional[str] = None

        # 加载Prompt文件
        self.prompts = self._load_prompts()

        # 缓存机制（用于演示优化）
        self._cache: Dict[str, List[Dict]] = {}

    def _load_prompts(self) -> Dict[str, str]:
        """加载三个角色的Prompt文件"""
        prompts = {}
        prompts_dir = os.path.join(os.path.dirname(__file__), "prompts")

        for role in ["advocate", "skeptic", "judge"]:
            file_path = os.path.join(prompts_dir, f"{role}.txt")
            try:
                with open(file_path, "r", encoding="utf-8") as f:
                    prompts[role] = f.read()
            except FileNotFoundError:
                prompts[role] = f"【{role}角色Prompt文件未找到，请检查路径】"
                print(f"⚠️ 未找到Prompt文件: {file_path}")

        return prompts

    def _get_detection_result(self, user_input: str) -> Dict:
        """获取偏差检测结果"""
        if UPSTREAM_READY:
            try:
                detector = BiasDetector()
                return detector.detect(user_input)
            except Exception as e:
                print(f"⚠️ 检测器调用失败，回退到Mock: {e}")
                return {"debate_focus": MOCK_DEBATE_FOCUS}
        else:
            return {"debate_focus": MOCK_DEBATE_FOCUS}

    def _format_focus_for_prompt(self, focus: Dict) -> str:
        """将debate_focus格式化为Prompt可用的字符串"""
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

    def _prepare_prompts(self, focus: Dict):
        """准备替换变量后的Prompt"""
        focus_str = self._format_focus_for_prompt(focus)

        self.prompts = {
            "advocate": self._base_prompts["advocate"].replace("{debate_focus}", focus_str),
            "skeptic": self._base_prompts["skeptic"].replace("{debate_focus}", focus_str),
            "judge": self._base_prompts["judge"].replace("{debate_focus}", focus_str),
        }

    @property
    def _base_prompts(self) -> Dict[str, str]:
        """获取原始Prompt（未替换变量）"""
        if not hasattr(self, '_prompts_cache'):
            self._prompts_cache = self._load_prompts()
        return self._prompts_cache

    def start(self, user_input: str) -> Generator[Dict, None, None]:
        """启动辩论流程"""
        self.user_input = user_input

        # 检查缓存
        cache_key = hash(user_input)
        if cache_key in self._cache:
            print("📦 使用缓存数据")
            for item in self._cache[cache_key]:
                yield item
            return

        # 获取偏差检测结果
        detection_result = self._get_detection_result(user_input)
        self.debate_focus = detection_result.get("debate_focus", MOCK_DEBATE_FOCUS)

        # 准备Prompt（替换变量）
        self.prompts = self._base_prompts.copy()
        focus_str = self._format_focus_for_prompt(self.debate_focus)
        for role in self.prompts:
            self.prompts[role] = self.prompts[role].replace("{debate_focus}", focus_str)

        # 初始化状态机
        self.state_machine = DebateStateMachine(max_rounds=3)

        # 运行辩论并收集结果（用于缓存）
        results = []
        for result in self._run_debate():
            results.append(result)
            yield result

        # 保存到缓存
        self._cache[cache_key] = results

    def _run_debate(self) -> Generator[Dict, None, None]:
        """运行辩论主循环"""
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
                return  # 暂停，等待用户输入

        # 辩论结束
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
        """正方发言"""
        system_prompt = self.prompts["advocate"]
        user_content = self.user_input

        # 构建历史上下文
        history = self._format_history_for_role("正方")

        content_parts = []
        for token in self.llm.chat(system_prompt, user_content, history, role="advocate"):
            content_parts.append(token)
            yield {
                "round": self.state_machine.round,
                "status": "advocate_turn",
                "speaker": "正方",
                "content": "".join(content_parts),
                "judge_data": None,
                "user_can_intervene": False
            }

        # 保存完整发言
        full_content = "".join(content_parts)
        self.state_machine.add_history("正方", full_content)

    def _skeptic_speak(self) -> Generator[Dict, None, None]:
        """反方发言"""
        system_prompt = self.prompts["skeptic"]

        # 获取正方发言作为输入
        round_history = self.state_machine.get_round_history()
        advocate_msgs = [h for h in round_history if h["speaker"] == "正方"]

        if advocate_msgs:
            user_content = advocate_msgs[-1]["content"]
        else:
            user_content = self.user_input

        history = self._format_history_for_role("反方")

        content_parts = []
        for token in self.llm.chat(system_prompt, user_content, history, role="skeptic"):
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
        """评委评估"""
        system_prompt = self.prompts["judge"]

        # 构建本轮辩论历史
        round_history = self.state_machine.get_round_history()
        history_text = "\n\n".join([
            f"【{h['speaker']}】{h['content']}"
            for h in round_history
        ])

        user_content = f"请基于以下本轮辩论内容给出评估：\n\n{history_text}"

        content_parts = []
        for token in self.llm.chat(system_prompt, user_content, role="judge"):
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

        # 解析评委JSON
        judge_data = self._parse_judge_json(full_content)

        # 根据评委判定更新状态
        if judge_data and judge_data.get("debate_status") == "concluded":
            self.state_machine.force_conclude()

        # 重新yield，包含解析后的数据
        yield {
            "round": self.state_machine.round,
            "status": "judge_turn",
            "speaker": "评委",
            "content": full_content,
            "judge_data": judge_data,
            "user_can_intervene": False
        }

    def _parse_judge_json(self, content: str) -> Optional[Dict]:
        """解析评委的JSON输出"""
        # 尝试直接解析
        try:
            return json.loads(content)
        except json.JSONDecodeError:
            pass

        # 尝试提取JSON块
        json_pattern = r'\{[\s\S]*?\}'
        matches = re.findall(json_pattern, content)

        for match in matches:
            try:
                return json.loads(match)
            except json.JSONDecodeError:
                continue

        # 回退：手动提取关键信息
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
        """格式化历史记录供LLM使用"""
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
        """用户插入回复后继续辩论"""
        self.state_machine.add_history("用户", reply_text)
        yield from self._run_debate()

    def generate_report(self) -> Dict:
        """生成最终偏差检测报告"""
        if not self.state_machine:
            return {"error": "辩论尚未开始"}

        judge_history = [
            h for h in self.state_machine.get_all_history()
            if h["speaker"] == "评委"
        ]

        # 提取所有评委判定
        judge_evaluations = []
        for h in judge_history:
            data = self._parse_judge_json(h["content"])
            if data:
                judge_evaluations.append(data)

        # 获取主偏差信息
        primary_bias = {}
        if judge_evaluations:
            last_eval = judge_evaluations[-1]
            primary_bias = {
                "bias_name": last_eval.get("primary_bias", "未知"),
                "confidence": last_eval.get("evaluation", {}).get("confidence", 0)
            }
        elif self.debate_focus:
            primary_bias = {
                "bias_name": self.debate_focus.get("primary_target", "未知"),
                "confidence": self.debate_focus.get("primary_confidence", 0)
            }

        # 计算风险等级
        risk_level = self._calculate_risk_level(judge_evaluations)

        # 获取最终建议
        final_suggestion = "无建议"
        if judge_evaluations:
            final_suggestion = judge_evaluations[-1].get("suggestion", "无建议")

        return {
            "debate_rounds": self.state_machine.round,
            "primary_bias": primary_bias,
            "secondary_biases": [],
            "judge_history": judge_evaluations,
            "final_suggestion": final_suggestion,
            "risk_level": risk_level
        }

    def _calculate_risk_level(self, evaluations: List[Dict]) -> str:
        """计算风险等级"""
        if not evaluations:
            return "低"

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
    print("🧪 DebateOrchestrator 完整测试")
    print("=" * 60)

    orch = DebateOrchestrator(provider='qwen', use_mock=True)

    print("\n🚀 启动辩论...")
    print("=" * 60)

    for r in orch.start('我已经投了这么多钱，必须坚持'):
        # 只显示最终完整内容
        if r['status'] in ['advocate_turn', 'skeptic_turn', 'judge_turn']:
            content = r['content']
            # 判断是否为最终输出（长度>20且以标点结尾）
            if len(content) > 20 and content[-1] in '。！？.!?':
                print(f'\n[{r["speaker"]}] {content}')
                if r['judge_data']:
                    print(f'  📊 评委数据: {json.dumps(r["judge_data"], ensure_ascii=False)}')

        elif r['status'] == 'waiting_user':
            print(f'\n[{r["speaker"]}] {r["content"]}')
            break

    # 模拟用户回复
    print('\n' + '=' * 60)
    print('💬 用户回复: 但是继续投入可能损失更多')
    print('=' * 60)

    for r in orch.user_reply('但是继续投入可能损失更多'):
        if r['status'] in ['advocate_turn', 'skeptic_turn', 'judge_turn']:
            content = r['content']
            if len(content) > 20 and content[-1] in '。！？.!?':
                print(f'\n[{r["speaker"]}] {content}')
                if r['judge_data']:
                    print(f'  📊 评委数据: {json.dumps(r["judge_data"], ensure_ascii=False)}')

    # 生成报告
    print('\n' + '=' * 60)
    print('📊 最终报告')
    print('=' * 60)
    report = orch.generate_report()
    print(json.dumps(report, ensure_ascii=False, indent=2))
