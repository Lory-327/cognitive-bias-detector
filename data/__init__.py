"""
data 包初始化文件

此包包含认知偏差知识库模块，供识别引擎调用。

主要暴露接口:
    - BIAS_DATABASE: 认知偏差结构化知识库 (dict)
    - CROSSOVER_ADJUSTMENT: 偏差交叉调整规则 (dict)
    - get_bias_info(bias_id): 查询偏差详情
    - get_crossover_adjustment(bias_a, bias_b): 查询交叉规则
    - get_biases_by_category(category): 按类别查询偏差
    - get_all_bias_names(): 获取所有偏差中文名
    - get_all_bias_ids(): 获取所有偏差英文ID
    - search_biases_by_keyword(keyword): 关键词搜索偏差

用法示例:
    >>> from data import BIAS_DATABASE, get_bias_info
    >>> info = get_bias_info("沉没成本谬误")
    >>> print(info["description"])
"""

from .bias_knowledge_base import (
    BIAS_DATABASE,
    CROSSOVER_ADJUSTMENT,
    get_bias_info,
    get_crossover_adjustment,
    get_biases_by_category,
    get_all_bias_names,
    get_all_bias_ids,
    search_biases_by_keyword,
)

__all__ = [
    "BIAS_DATABASE",
    "CROSSOVER_ADJUSTMENT",
    "get_bias_info",
    "get_crossover_adjustment",
    "get_biases_by_category",
    "get_all_bias_names",
    "get_all_bias_ids",
    "search_biases_by_keyword",
]

# 包级别元信息
__version__ = "1.0.0"
__author__ = "认知偏差知识库负责人"
__total_biases__ = len(BIAS_DATABASE)
__total_crossover_rules__ = len(CROSSOVER_ADJUSTMENT)