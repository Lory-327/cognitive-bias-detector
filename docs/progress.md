"""
认知偏差检测器 - 项目入口
运行: python main.py
"""

from config import check_api_key


def welcome():
    print("=" * 60)
    print("🧠 认知偏差检测器 - 三角色AI决策分析系统")
    print("=" * 60)
    print("\n项目成员:")
    print("  崔庆芳 - 认知偏差知识库")
    print("  杨惠蓝 - 输入解析引擎")
    print("  韩琴   - 偏差识别引擎")
    print("  罗晓玲 - 三角色AI辩论编排")
    print("\n状态检查...")
    
    # 检查API配置
    api_ready = check_api_key()
    
    print("\n模块检查:")
    try:
        from data import bias_knowledge_base
        print("  ✅ data/bias_knowledge_base.py 已加载")
    except ImportError as e:
        print(f"  ❌ data/bias_knowledge_base.py 加载失败: {e}")
    
    try:
        from core import input_parser
        print("  ✅ core/input_parser.py 已加载")
    except ImportError as e:
        print(f"  ❌ core/input_parser.py 加载失败: {e}")
    
    try:
        from core import bias_detector
        print("  ✅ core/bias_detector.py 已加载")
    except ImportError as e:
        print(f"  ❌ core/bias_detector.py 加载失败: {e}")
    
    try:
        from debate import debate_orchestrator
        print("  ✅ debate/debate_orchestrator.py 已加载")
    except ImportError as e:
        print(f"  ❌ debate/debate_orchestrator.py 加载失败: {e}")
    
    print("\n" + "=" * 60)
    print("项目初始化完成！等待模块开发...")
    print("=" * 60)


if __name__ == "__main__":
    welcome()

| 2026-06-11 | 组长 | 项目初始化完成，GitHub仓库创建并推送 | 无 | 等待成员克隆 |
| 2026-06-11 | 杨惠蓝 | 提交 input_parser.py 初版，decision_type识别正确，假设/情绪/成本待完善 | 无 | 待完善后重新测试 |
| 2026-06-11 | 韩琴 | 待开始集成 | 等待杨惠蓝完善 | 先用Mock数据开发 |