import re
import jieba
from typing import Dict, Any, List, TypedDict

class TimePressureDict(TypedDict):
    has_pressure: bool
    pressure_level: str
    keywords: List[str]


class AlternativesDict(TypedDict):
    considered_alternatives: bool
    explicitly_rejected_alternatives: bool
    evidence: List[str]


class KeyElementsDict(TypedDict):
    decision_target: Any  # str or None
    stated_reason: List[str]
    numbers: List[str]


class EmotionTagDict(TypedDict):
    emotion: str
    intensity: str


class ParserOutputContract(TypedDict):
    original_text: str
    cleaned_text: str
    decision_type: str
    key_elements: KeyElementsDict
    implied_assumptions: List[str]
    emotion_tags: List[EmotionTagDict]
    cost_signals: List[str]
    time_pressure: TimePressureDict
    alternatives: AlternativesDict


class InputParser:
    def __init__(self, custom_types: Dict[str, List[str]] = None):
        # 1. 22种全场景决策类型精细化词库
        self.decision_types: Dict[str, List[str]] = {
            "购房置业": ["买房", "购房", "看房", "楼盘", "首付", "房贷", "买套房", "置业", "二手房", "学区房", "落户",
                         "收房"],
            "金融投资": ["股票", "基金", "投资", "炒股", "理财", "加仓", "亏损", "赚钱", "数字货币", "比特币", "定投",
                         "大盘", "黄金", "期货"],
            "职业规划": ["辞职", "换工作", "跳槽", "找工作", "面试", "行业", "前途", "职业", "老板", "公司", "转行",
                         "下家", "职场"],
            "日常消费": ["买手机", "消费", "购物", "大件", "剁手", "下单", "买个", "包包", "奢侈品", "微单", "配置",
                         "性价比", "种草"],
            "情感人际": ["分手", "表白", "谈恋爱", "相亲", "前任", "彩礼", "结婚", "追她", "绝交", "吵架", "喜欢的人",
                         "复合", "恋情"],
            "教育深造": ["选专业", "留学", "报班", "考证", "补习", "雅思", "托福", "读博", "选修课", "MBA", "绩点",
                         "挂科"],
            "创业搞钱": ["开店", "合伙", "副业", "摆摊", "加盟", "创业", "拉投资", "工作室", "自媒体", "网店",
                         "前期投入"],
            "健康医疗": ["医美", "减肥", "做手术", "健身房", "私教", "看病", "正畸", "植发", "近视手术", "体检",
                         "买保险", "住院"],
            "学历考试": ["考研", "考公", "编制", "体制内", "上岸", "考编", "笔试", "国考", "省考", "调剂", "二战",
                         "复试"],
            "宠物养育": ["养狗", "养猫", "宠物", "铲屎官", "猫粮", "狗粮", "绝育", "吸猫", "品相", "纯种", "领养",
                         "驱虫"],
            "车辆出行": ["买车", "提车", "新能源", "驾照", "车牌", "4S店", "摇号", "油耗", "置换", "改车", "试驾"],
            "人脉应酬": ["请客", "送礼", "随份子", "酒局", "饭局", "人情世故", "托关系", "走后门", "拉关系", "应酬"],
            "生活娱乐": ["追星", "演唱会", "门票", "旅游", "看电影", "网游", "氪金", "充值", "手办", "买周边", "出游"],
            "房屋租赁": ["租房", "房东", "合租", "押一付三", "转租", "中介费", "退押金", "续租", "室友", "找房"],
            "自我提升": ["自学", "读书", "戒律", "极简", "自律", "早起", "习惯", "时间管理", "知识付费", "上网课"],
            "法律维权": ["起诉", "打官司", "维权", "合同", "律师", "劳动仲裁", "赔偿", "举报", "侵权", "调解"],
            "美容时尚": ["穿搭", "护肤品", "做发型", "烫发", "染发", "整容", "美甲", "买衣服", "化妆品"],
            "数码科技": ["组装机", "显卡", "升级系统", "路由器", "智能家居", "换电脑", "平板", "评测"],
            "家庭育儿": ["早教", "幼儿园", "奶粉", "生娃", "坐月子", "备孕", "学区", "玩具", "补习班"],
            "养老规划": ["养老院", "退休金", "社保", "医保", "定期存款", "防老", "人寿保险", "财产继承"],
            "公益慈善": ["捐款", "志愿者", "支教", "众筹", "放生", "公益活动", "红十字", "支农"],
            "休闲爱好": ["钓鱼", "摄影", "文玩", "露营", "徒步", "桌游", "剧本杀", "潜水", "滑雪"]
        }

        # 支持动态注入外部自定义决策类型
        if custom_types:
            self.decision_types.update(custom_types)

        # 2. 5种隐含假设触发词库
        self.assumption_rules: Dict[str, List[str]] = {
            "past_equals_future": ["一直涨", "一直在涨", "必定赚", "稳赚不赔", "不可能跌", "历史规律", "牛市",
                                   "当年也是", "以后也会", "每次都"],
            "sunk_cost_continuation": ["已经亏了", "已经投了", "付了定金", "花了这么多钱", "不能白白", "舍不得", "套牢",
                                       "心疼之前的", "坚持了这么久", "沉没成本"],
            "peer_experience_equals_my_result": ["朋友说", "亲戚说", "大家都", "很多人都在", "跟风", "专家推荐",
                                                 "听人说", "小红书推荐", "博主说", "围观"],
            "information_equals_accuracy": ["查了好多资料", "做了大量功功课", "研究了很久", "绝对靠谱", "百分之百确定",
                                            "看透了", "数据都对比过"],
            "scarcity_requires_action": ["最后一套", "再不买就没了", "限时特惠", "手慢无", "错过就没了", "千载难逢",
                                         "倒计时", "绝版", "清仓"]
        }

        # 3. 情绪特征词典
        self.emotion_lexicon: Dict[str, List[str]] = {
            "焦虑": ["焦虑", "睡不着", "发愁", "怎么办", "好烦", "迷茫", "无助", "恐慌", "压力大"],
            "犹豫": ["纠结", "犹豫", "拿不定主意", "摇摆", "考虑", "纠缠", "难以抉择", "看情况"],
            "自信": ["稳了", "有把握", "肯定", "绝对", "必然", "没问题", "百分之百", "确定"],
            "从众": ["随大流", "跟着买", "听说好", "大家都说", "爆款", "网红", "跟风"],
            "后悔": ["早知道", "后悔", "早该", "当初", "要是...就好了", "亏大了", "白干了"]
        }

        # 否定前缀过滤词
        self.negation_words = ["不", "没", "别", "不要", "从不", "并非"]

    def _clean_text(self, text: str) -> str:
        if not text:
            return ""
        text = text.strip()
        text = text.replace("?", "？").replace("!", "！").replace(",", "，")
        return text

    def _extract_decision_type(self, tokens: List[str]) -> str:
        scores = {k: 0 for k in self.decision_types.keys()}

        for i, token in enumerate(tokens):
            for d_type, keywords in self.decision_types.items():
                if token in keywords:
                    if i > 0 and tokens[i - 1] in self.negation_words:
                        continue
                    scores[d_type] += 1

        best_match = max(scores, key=scores.get)
        return best_match if scores[best_match] > 0 else "未分类"

    def _extract_key_elements(self, text: str, tokens: List[str], decision_type: str) -> KeyElementsDict:
        """ 动态提取决策三要素 """
        number_pattern = r'[0-9一二三四五六七八九十百千万亿\%百分点\.]+'
        found_numbers = re.findall(number_pattern, text)
        cleaned_numbers = [num for num in found_numbers if num.strip()]

        decision_target = None
        if decision_type != "未分类":
            for token in tokens:
                if token in self.decision_types[decision_type]:
                    decision_target = token
                    break

        reasons = []
        reason_markers = ["因为", "由于", "理由是", "为了", "主要考虑到"]
        for marker in reason_markers:
            if marker in text:
                parts = text.split(marker)
                if len(parts) > 1:
                    reasons.append(parts[1][:15].strip())

        return {
            "decision_target": decision_target,
            "stated_reason": reasons,
            "numbers": cleaned_numbers
        }

    def _extract_implied_assumptions(self, text: str) -> List[str]:
        """ 心理学底层盲区感知 """
        matched_assumptions = []
        for assumption_code, keywords in self.assumption_rules.items():
            for word in keywords:
                if word in text:
                    if assumption_code not in matched_assumptions:
                        matched_assumptions.append(assumption_code)
        return matched_assumptions

    def _analyze_emotions(self, text: str) -> List[EmotionTagDict]:
        """ 情绪强度双谱流计算 """
        tags: List[EmotionTagDict] = []
        for emotion, keywords in self.emotion_lexicon.items():
            count = sum(1 for word in keywords if word in text)
            if count > 0:
                intensity = "高" if count >= 2 else "中"
                tags.append({"emotion": emotion, "intensity": intensity})
        return tags

    def _detect_time_pressure(self, text: str) -> TimePressureDict:
        """ 决策窗口紧迫度动态分析 """
        pressure_keywords = ["来不及了", "赶紧", "立马", "马上", "限时", "快要", "倒计时", "抓紧"]
        found_words = [word for word in pressure_keywords if word in text]

        has_pressure = len(found_words) > 0
        level = "无"
        if has_pressure:
            level = "高" if len(found_words) >= 2 or "来不及" in text else "中"

        return {
            "has_pressure": has_pressure,
            "pressure_level": level,
            "keywords": found_words
        }

    def _detect_alternatives(self, text: str) -> AlternativesDict:
        """ 贝叶斯思维备选空间检验 """
        alternative_words = ["或者", "要么", "Plan B", "备选", "另一条路", "两手准备"]
        reject_words = ["别无选择", "只能这样", "没办法", "必须要"]

        has_alt = any(w in text for w in alternative_words)
        has_reject = any(w in text for w in reject_words)

        evidence = []
        if has_alt: evidence.append("检测到多路径备选词汇")
        if has_reject: evidence.append("检测到极端路径强迫词汇")

        return {
            "considered_alternatives": has_alt,
            "explicitly_rejected_alternatives": has_reject,
            "evidence": evidence
        }

    def extract(self, text: str) -> ParserOutputContract:
        # 1. 文本预处理清洗
        cleaned_text = self._clean_text(text)

        # 2. 精准分词
        tokens = list(jieba.cut(cleaned_text))

        # 3. 核心管道链式解析
        decision_type = self._extract_decision_type(tokens)
        key_elements = self._extract_key_elements(cleaned_text, tokens, decision_type)
        implied_assumptions = self._extract_implied_assumptions(cleaned_text)
        emotion_tags = self._analyze_emotions(cleaned_text)
        time_pressure = self._detect_time_pressure(cleaned_text)
        alternatives = self._detect_alternatives(cleaned_text)

        # 金额与开销资产信号交叉提炼
        cost_signals = [num for num in key_elements["numbers"] if
                        any(unit in num for unit in ["万", "元", "块", "千", "刀", "币"])]

        # 4. 严格返回类型保证
        return {
            "original_text": text,
            "cleaned_text": cleaned_text,
            "decision_type": decision_type,
            "key_elements": key_elements,
            "implied_assumptions": implied_assumptions,
            "emotion_tags": emotion_tags,
            "cost_signals": cost_signals,
            "time_pressure": time_pressure,
            "alternatives": alternatives
        }



if __name__ == "__main__":
    parser = InputParser()

    # 终极严苛测试用例组
    ultimate_cases = [
        "今年为了能成功上岸体制内，我已经决定二战考研了，每天发愁得睡不着，焦虑死了。看到大家都去报了那个一万块的保过班，我也得抓紧把钱交了，再不报就真的来不及了，感觉自己别无选择啊！",
        "听说养狗很治愈，我最近也打算领养一只纯种猫，猫粮和駆虫药已经花了五百块了，虽然心里很纠结、很犹豫，但实在太喜欢它了，只能这样了。",
        "下个月放假想出门找个安静的地方钓鱼或者露营，我不买房，也不打算换工作，纯放松。",
        "听说由于起诉老板进行劳动仲裁研究了很久，绝对靠谱，律师费需要两万块，哪怕赔偿没多少我也不能白白浪费之前的精力！"
    ]

    for idx, case in enumerate(ultimate_cases, 1):
        res = parser.extract(case)
        print(f"\n [天花板解析器 - 严苛测试案例 {idx}]")
        print(f"├─ 原始输入 : {res['original_text']}")
        print(f"├─ 清洗文本 : {res['cleaned_text']}")
        print(
            f"├─ 决策判定 : \033[1;32m{res['decision_type']}\033[0m (命中目标词: {res['key_elements']['decision_target']})")
        print(f"├─ 数字资产 : {res['key_elements']['numbers']} | 提取理由: {res['key_elements']['stated_reason']}")
        print(f"├─ 财务信号 : {res['cost_signals']}")
        print(f"├─ 认知盲区 : \033[1;31m{res['implied_assumptions']}\033[0m")
        print(f"├─ 情绪特征 : {res['emotion_tags']}")
        print(f"├─ 窗口压力 : {res['time_pressure']}")
        print(f"└─ 方案冗余 : {res['alternatives']}")