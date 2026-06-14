"""
debate 包 - 三角色AI辩论系统

包含模块:
- llm_client: 大模型API客户端
- state_machine: 辩论状态机
- debate_orchestrator: 辩论编排器
"""

from debate.llm_client import LLMClient
from debate.state_machine import DebateStateMachine, DebateState
from debate.debate_orchestrator import DebateOrchestrator

__all__ = [
    "LLMClient",
    "DebateStateMachine",
    "DebateState",
    "DebateOrchestrator",
]
