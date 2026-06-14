from enum import Enum, auto
from typing import List, Dict


class DebateState(Enum):
    """辩论状态枚举"""
    INIT = "init"
    ADVOCATE_TURN = "advocate_turn"
    SKEPTIC_TURN = "skeptic_turn"
    JUDGE_TURN = "judge_turn"
    WAITING_USER = "waiting_user"
    CONCLUDED = "concluded"


class DebateStateMachine:
    """辩论状态机 - 管理辩论流程"""

    def __init__(self, max_rounds: int = 3):
        self.state = DebateState.INIT
        self.round = 0
        self.max_rounds = max_rounds
        self.history: List[Dict] = []

    def next(self) -> DebateState:
        """状态流转"""
        if self.state == DebateState.INIT:
            self.state = DebateState.ADVOCATE_TURN
            self.round = 1

        elif self.state == DebateState.ADVOCATE_TURN:
            self.state = DebateState.SKEPTIC_TURN

        elif self.state == DebateState.SKEPTIC_TURN:
            self.state = DebateState.JUDGE_TURN

        elif self.state == DebateState.JUDGE_TURN:
            if self.round >= self.max_rounds:
                self.state = DebateState.CONCLUDED
            else:
                self.state = DebateState.WAITING_USER

        elif self.state == DebateState.WAITING_USER:
            self.round += 1
            self.state = DebateState.ADVOCATE_TURN

        return self.state

    def should_continue(self) -> bool:
        """判断是否继续辩论"""
        return self.state not in [
            DebateState.CONCLUDED,
            DebateState.WAITING_USER
        ]

    def is_waiting_user(self) -> bool:
        """是否在等待用户输入"""
        return self.state == DebateState.WAITING_USER

    def is_concluded(self) -> bool:
        """辩论是否已结束"""
        return self.state == DebateState.CONCLUDED

    def add_history(self, speaker: str, content: str):
        """添加对话记录"""
        self.history.append({
            "round": self.round,
            "speaker": speaker,
            "content": content
        })

    def get_round_history(self, round_num: int = None) -> List[Dict]:
        """获取指定轮次的对话历史"""
        if round_num is None:
            round_num = self.round
        return [h for h in self.history if h["round"] == round_num]

    def get_all_history(self) -> List[Dict]:
        """获取全部历史"""
        return self.history.copy()

    def force_conclude(self):
        """强制结束辩论"""
        self.state = DebateState.CONCLUDED


if __name__ == "__main__":
    sm = DebateStateMachine(max_rounds=2)

    print(f"初始状态: {sm.state.value}")

    while sm.state != DebateState.CONCLUDED:
        current = sm.next()
        print(f"→ 状态: {current.value}, 轮数: {sm.round}")

        if current == DebateState.ADVOCATE_TURN:
            sm.add_history("正方", "正方发言")
        elif current == DebateState.SKEPTIC_TURN:
            sm.add_history("反方", "反方发言")
        elif current == DebateState.JUDGE_TURN:
            sm.add_history("评委", '{"debate_status": "continuing"}')
            if sm.round == 1:
                sm.next()
                sm.add_history("用户", "用户回复")

        print(f"  是否继续: {sm.should_continue()}")

    print(f"\n最终状态: {sm.state.value}")
    print(f"总轮数: {sm.round}")
    print(f"历史记录数: {len(sm.history)}")
