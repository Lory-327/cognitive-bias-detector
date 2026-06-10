"""
大模型API配置
每个成员本地创建 .env 文件填入自己的API密钥，不要提交到Git
"""

import os
from pathlib import Path

# 尝试加载 .env 文件（如果安装了 python-dotenv）
try:
    from dotenv import load_dotenv
    env_path = Path(__file__).parent / '.env'
    if env_path.exists():
        load_dotenv(env_path)
except ImportError:
    pass

# 选择模型提供商（修改这里切换模型）
LLM_PROVIDER = "deepseek"  # 可选: "openai", "deepseek", "zhipu"

# API密钥（从环境变量读取，不要在代码中写死！）
API_KEYS = {
    "openai": os.getenv("OPENAI_API_KEY", ""),
    "deepseek": os.getenv("DEEPSEEK_API_KEY", ""),
    "zhipu": os.getenv("ZHIPU_API_KEY", ""),
}

# API基础地址
BASE_URLS = {
    "openai": "https://api.openai.com/v1",
    "deepseek": "https://api.deepseek.com/v1",
    "zhipu": "https://open.bigmodel.cn/api/paas/v4",
}

# 模型名称
MODEL_NAMES = {
    "openai": "gpt-4o-mini",      # 便宜，效果够用
    "deepseek": "deepseek-chat",    # 性价比最高，推荐
    "zhipu": "glm-4",               # 清华系，中文好
}

def get_api_config(provider: str = None):
    """获取指定provider的完整配置"""
    p = provider or LLM_PROVIDER
    return {
        "api_key": API_KEYS.get(p, ""),
        "base_url": BASE_URLS.get(p, ""),
        "model": MODEL_NAMES.get(p, ""),
    }

def check_api_key():
    """检查当前provider的API密钥是否已配置"""
    config = get_api_config()
    if not config["api_key"]:
        print(f"警告: {LLM_PROVIDER} 的API密钥未配置！")
        print(f"请在项目根目录创建 .env 文件，添加 {LLM_PROVIDER.upper()}_API_KEY=你的密钥")
        return False
    print(f"当前使用模型: {LLM_PROVIDER} ({config['model']})")
    return True

if __name__ == "__main__":
    check_api_key()