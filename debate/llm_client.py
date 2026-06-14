import os
import time
import json
from pathlib import Path
from typing import Generator, List, Dict, Optional

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

PROJECT_ROOT = Path(__file__).parent.parent
load_env_file(PROJECT_ROOT / ".env")

try:
    import requests
except ImportError:
    print("❌ 需要安装 requests: python -m pip install requests")
    raise


class LLMClient:
    """大模型API客户端 - 支持阿里云百炼(Qwen)"""

    PROVIDERS = {
        "qwen": {
            "base_url": "https://dashscope.aliyuncs.com/compatible-mode/v1",
            "model": "qwen-turbo",
            "env_key": "DASHSCOPE_API_KEY"
        },
        "qwen-plus": {
            "base_url": "https://dashscope.aliyuncs.com/compatible-mode/v1",
            "model": "qwen-plus",
            "env_key": "DASHSCOPE_API_KEY"
        }
    }

    def __init__(self, provider: str = "qwen", use_mock: bool = False):
        self.provider = provider
        self.use_mock = use_mock

        config = self.PROVIDERS.get(provider, self.PROVIDERS["qwen"])
        self.base_url = config["base_url"]
        self.model = config["model"]
        self.env_key = config["env_key"]

        self.api_key = os.getenv(self.env_key)

        if not self.api_key and not self.use_mock:
            print(f"⚠️ 未配置 {self.env_key}，切换到 Mock 模式")
            self.use_mock = True

        if not self.use_mock:
            print(f"✅ 使用 {provider} API: {self.model}")

    def chat(
        self,
        system_prompt: str,
        user_content: str,
        history: Optional[List[Dict]] = None,
        role: str = None
    ) -> Generator[str, None, None]:
        """流式对话"""
        if self.use_mock:
            detected_role = role or self._detect_role(system_prompt)
            yield from self._mock_chat_by_role(detected_role)
            return

        messages = [{"role": "system", "content": system_prompt}]
        if history:
            messages.extend(history)
        messages.append({"role": "user", "content": user_content})

        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }

        data = {
            "model": self.model,
            "messages": messages,
            "stream": True
        }

        for attempt in range(3):
            try:
                response = requests.post(
                    f"{self.base_url}/chat/completions",
                    headers=headers,
                    json=data,
                    stream=True,
                    timeout=30
                )

                if response.status_code != 200:
                    raise Exception(f"HTTP {response.status_code}: {response.text[:200]}")

                for line in response.iter_lines():
                    if line:
                        line = line.decode('utf-8')
                        if line.startswith('data: '):
                            json_str = line[6:]
                            if json_str == '[DONE]':
                                return
                            try:
                                chunk = json.loads(json_str)
                                delta = chunk['choices'][0]['delta']
                                if 'content' in delta and delta['content']:
                                    yield delta['content']
                            except:
                                continue
                return

            except Exception as e:
                if attempt < 2:
                    time.sleep(2 ** attempt)
                else:
                    yield f"\n[系统提示：AI服务暂时不可用。错误：{str(e)}]"
                    return

    def _detect_role(self, system_prompt: str) -> str:
        """检测角色"""
        sp = system_prompt.lower()
        if "advocate" in sp or "正方" in sp or "辩护" in sp:
            return "advocate"
        elif "skeptic" in sp or "反方" in sp or "质疑" in sp or "追问" in sp:
            return "skeptic"
        elif "judge" in sp or "评委" in sp:
            return "judge"
        return "unknown"

    def _mock_chat_by_role(self, role: str) -> Generator[str, None, None]:
        """按角色返回 Mock 内容"""
        responses = {
            "advocate": "您的决策有其合理性。从已有信息来看，继续推进可以充分利用已投入的资源，避免前期努力付诸东流。",
            "skeptic": "如果不考虑已经投入的成本，您还会做同样的选择吗？这是一个关键的思考角度。",
            "judge": '{"round": 1, "primary_bias": "沉没成本谬误", "debate_status": "continuing", "next_focus": "验证投入是否可收回", "suggestion": "建议重新评估决策的独立价值", "evaluation": {"bias_probability": 75, "impact_level": "高", "confidence": 0.8}}',
            "unknown": "模拟回复。"
        }
        yield responses.get(role, responses["unknown"])

    def chat_sync(self, system_prompt: str, user_content: str, history=None, role=None) -> str:
        """同步调用"""
        return "".join(self.chat(system_prompt, user_content, history, role=role))


if __name__ == "__main__":
    print("=" * 50)
    print("🧪 LLMClient 测试")
    print("=" * 50)

    client = LLMClient(use_mock=True)

    tests = [
        ("advocate", "正方测试"),
        ("skeptic", "反方测试"),
        ("judge", "评委测试"),
    ]

    for role, label in tests:
        print(f"\n🧪 {label}:")
        for token in client.chat("system", "user", role=role):
            print(token)

    print("\n✅ 全部完成！")
