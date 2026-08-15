"""食材/调料分类器：把 AI 抽取出的食材列表中混入的调料自动识别并拆出。

纯规则、确定性实现（不依赖额外 LLM 调用），保证任何模型的抽取结果都会被统一归类：
- 精确/子串命中常见调料名（盐/生抽/料酒/花椒…）→ 调料；
- 以"油"结尾的油脂类（排除 黄油/牛油/奶油/板油 等食材）→ 调料；
- 完整名命中排除表（洋葱/蒜苔/奶糖… 虽含调料子串但是真实食材）→ 保留为食材。

与移植的 cook 调料模块保持一致：调料单独建表（seasonings / recipe_seasonings），
不再与食材混存 recipe_ingredients。
"""
from typing import Dict, List, Optional, Set, Tuple

# 调料关键词：子串命中即视为调料（同时覆盖精确名与常见复合名）
SEASONING_KEYWORDS = (
    # 基础调味
    "盐", "糖", "醋", "蜂蜜", "味精", "鸡精", "鸡粉", "鸡汁", "糖浆", "麦芽糖",
    # 酱油 / 酒类
    "生抽", "老抽", "酱油", "豉油", "味极鲜", "蚝油", "鱼露",
    "料酒", "黄酒", "米酒", "醪糟", "酒酿",
    # 酱料
    "豆瓣酱", "甜面酱", "黄豆酱", "番茄酱", "辣椒酱", "芝麻酱", "花生酱",
    "沙拉酱", "千岛酱", "蛋黄酱", "烧烤酱", "烧烤料", "沙茶酱", "海鲜酱", "叉烧酱",
    "柱侯酱", "蒜蓉辣酱", "韩式辣酱", "老干妈", "腐乳", "南乳", "豆豉",
    "芥末", "山葵", "沙司",
    # 香料
    "花椒", "藤椒", "麻椒", "八角", "大料", "桂皮", "香叶", "丁香", "草果",
    "白芷", "甘草", "小茴香", "孜然", "五香粉", "十三香", "咖喱",
    "迷迭香", "百里香", "罗勒", "牛至", "紫苏", "香茅", "山奈", "沙姜",
    "陈皮", "高汤",
    # 葱姜蒜等调味菜（本系统约定为香料；洋葱/蒜苔等除外）
    "葱", "姜", "蒜",
    # 粉 / 干辣椒 / 发酵辅料
    "辣椒粉", "辣椒面", "胡椒粉", "花椒粉", "孜然粉", "淀粉", "生粉", "芡粉",
    "小苏打", "泡打粉", "酵母", "干辣椒", "泡椒", "剁椒", "油泼辣子",
)

# 含调料子串但不是调料的完整食材名
SEASONING_EXCLUSIONS = frozenset({
    "洋葱", "圆葱", "洋葱丁", "洋葱丝", "洋葱碎", "洋葱末", "洋葱圈",
    "紫洋葱", "白洋葱", "红洋葱", "黄洋葱",
    "蒜苔", "蒜薹", "蒜苗", "蒜黄",
    "奶糖", "口香糖", "糖果", "水果糖",
    "盐田虾", "盐焗鸡", "糖醋排骨", "醋溜白菜",
    "豆豉鲮鱼", "酱油肉", "丁香鱼",
})

# 结尾为"油"的油脂类调料；以下完整名虽然结尾带"油"但是真实食材
SEASONING_OIL_SUFFIX = "油"
SEASONING_OIL_SUFFIX_EXCLUSIONS = frozenset({"黄油", "牛油", "奶油", "板油", "淡奶油"})


def is_seasoning(name: str, known_seasonings: Optional[Set[str]] = None) -> bool:
    """判断一个食材名是否为调料。

    known_seasonings: 已存在的调料名集合（来自调料表），精确命中即为调料，
    用于兜底覆盖静态词典未收录、但用户已在调料表中手工维护过的条目。
    """
    if not name:
        return False
    name = name.strip()
    if not name:
        return False
    if known_seasonings and name in known_seasonings:
        return True
    if name in SEASONING_EXCLUSIONS:
        return False
    if name in SEASONING_OIL_SUFFIX_EXCLUSIONS:
        return False
    if name.endswith(SEASONING_OIL_SUFFIX):
        return True
    for kw in SEASONING_KEYWORDS:
        if kw in name:
            return True
    return False


def split_ingredients(
    ingredients: List[Dict],
    known_seasonings: Optional[Set[str]] = None,
) -> Tuple[List[Dict], List[Dict]]:
    """把食材列表拆成 (真实食材, 调料)。每条保留原字段（name/quantity/unit 等）。"""
    real: List[Dict] = []
    seasonings: List[Dict] = []
    for ing in ingredients or []:
        name = (ing.get("name") or "").strip()
        if not name:
            continue
        if is_seasoning(name, known_seasonings):
            seasonings.append(ing)
        else:
            real.append(ing)
    return real, seasonings
