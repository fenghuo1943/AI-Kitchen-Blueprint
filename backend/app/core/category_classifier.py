"""食材/调料/菜谱规则分类器（确定性、无 LLM / DB 依赖）。

镜像 core/seasoning_classifier.py 的风格：纯规则实现，保证任何来源的数据
（AI 采集 / 手动录入 / 迁移）都会被统一归类。

- classify_ingredient / classify_seasoning / classify_recipe 返回规范分类名
  （见 CATEGORY_LISTS）；无法识别返回 None，由调用方回落「默认」分类。
- classify_ingredient 首步复用 seasoning_classifier.is_seasoning 判定调料，
  避免「料酒 / 姜 / 大蒜」被误塞进食材分类。
"""
from dataclasses import dataclass
from typing import Dict, FrozenSet, List, Optional, Tuple

from app.core.seasoning_classifier import is_seasoning

# ============================================================
# 规范化分类清单（单一事实来源，P0/P1/P2 共用）
# ============================================================
INGREDIENT_CATEGORIES = (
    "蔬菜", "肉类", "海鲜水产", "蛋类", "豆制品",
    "菌菇", "谷薯主食", "水果", "乳品烘焙", "默认",
)
SEASONING_CATEGORIES = (
    "基础调味", "酱料", "去腥增香", "辣味调料", "香辛料", "粉末调料", "油脂", "默认",
)
RECIPE_CATEGORIES = (
    "家常菜", "快手菜", "汤羹", "凉菜", "面食", "炖菜", "减脂餐", "甜点", "默认",
)
CATEGORY_LISTS: dict[str, Tuple[str, ...]] = {
    "ingredient": INGREDIENT_CATEGORIES,
    "seasoning": SEASONING_CATEGORIES,
    "recipe": RECIPE_CATEGORIES,
}


@dataclass(frozen=True)
class Rule:
    """单条分类规则。

    exact: 归一后全等即命中（专名优先，消解子串歧义）。
    contains: 子串命中即命中。
    exclude: 完整名命中则强制不匹配本规则（子串误伤保护）。
    """
    category: str
    contains: Tuple[str, ...] = ()
    exact: FrozenSet[str] = frozenset()
    exclude: FrozenSet[str] = frozenset()


# ============================================================
# 食材规则（顺序影响同长度关键词的平局归属，如「虾米」→ 海鲜 而非 谷薯）
# ============================================================
INGREDIENT_RULES: Tuple[Rule, ...] = (
    # 海鲜水产（排在谷薯主食前，保证 虾米→海鲜）
    Rule(
        "海鲜水产",
        contains=(
            "三文鱼", "金枪鱼", "秋刀鱼", "黄花鱼", "多宝鱼", "鲈鱼", "带鱼", "鳕鱼",
            "草鱼", "鲤鱼", "鲫鱼", "鲅鱼", "墨鱼", "鱿鱼", "章鱼", "鳗鱼", "银鱼",
            "海参", "鲍鱼", "虾仁", "虾米", "虾皮", "小龙虾", "基围虾", "河虾",
            "蛤蜊", "花蛤", "扇贝", "牡蛎", "生蚝", "青口", "淡菜", "海带", "紫菜",
            "海苔", "鱼丸", "鱼片", "蟹柳", "田螺", "花螺",
            "鱼", "虾", "蟹", "贝", "螺",
        ),
        exclude=frozenset({"鱼露", "鱼籽", "蟹粉"}),
    ),
    # 蛋类
    Rule(
        "蛋类",
        contains=("鸡蛋", "鸭蛋", "皮蛋", "松花蛋", "咸鸭蛋", "鹌鹑蛋", "鸽子蛋", "鹅蛋",
                  "蛋黄", "蛋白", "蛋液", "蛋清", "蛋"),
    ),
    # 肉类
    Rule(
        "肉类",
        contains=(
            "五花肉", "里脊", "排骨", "肋排", "鸡翅", "鸡腿", "鸡胸", "鸡爪",
            "牛腩", "牛肋条", "牛腱", "牛尾", "牛肚", "羊排", "猪蹄", "猪脚",
            "猪肚", "猪肝", "猪腰", "肥肠", "培根", "香肠", "腊肉", "腊肠",
            "火腿", "午餐肉", "肉丸", "肉末", "肉丝", "肉片", "肉馅", "鸭血",
            "猪肉", "牛肉", "羊肉", "鸡肉", "鸭肉", "鹅肉", "兔肉", "驴肉",
            "肉",
        ),
        exclude=frozenset({"肉松", "牛油", "羊油", "猪油"}),
    ),
    # 豆制品
    Rule(
        "豆制品",
        contains=("豆腐", "豆干", "豆腐干", "豆皮", "腐竹", "豆浆", "千张", "百叶",
                  "素鸡", "油豆腐", "黄豆", "红豆", "绿豆", "黑豆", "豆沙", "豆乳",
                  "豆丝", "豆"),
        exclude=frozenset({"豆芽", "绿豆芽", "黄豆芽", "豆角", "油豆角", "四季豆", "荷兰豆", "豇豆", "豌豆"}),
    ),
    # 菌菇
    Rule(
        "菌菇",
        contains=("香菇", "金针菇", "杏鲍菇", "平菇", "茶树菇", "白玉菇", "海鲜菇",
                  "秀珍菇", "口蘑", "冬菇", "草菇", "猴头菇", "牛肝菌", "松茸",
                  "羊肚菌", "鸡枞菌", "木耳", "银耳", "竹荪", "菇"),
    ),
    # 蔬菜（含兜底 菜/萝卜/椒/瓜 等常见子串）
    Rule(
        "蔬菜",
        contains=(
            "白菜", "菠菜", "青菜", "油菜", "生菜", "空心菜", "韭菜", "芹菜", "香菜",
            "西兰花", "花菜", "菜花", "卷心菜", "甘蓝", "青椒", "彩椒", "甜椒", "尖椒",
            "辣椒", "小米辣", "番茄", "西红柿", "黄瓜", "丝瓜", "苦瓜", "冬瓜", "南瓜", "西葫芦",
            "茄子", "胡萝卜", "白萝卜", "红萝卜", "水萝卜", "萝卜", "莲藕", "藕",
            "豆角", "四季豆", "油豆角", "豇豆", "荷兰豆", "豌豆", "洋葱", "圆葱",
            "豆芽", "绿豆芽", "黄豆芽", "莴笋", "竹笋", "芦笋", "茭白", "蒜苔", "蒜薹",
            "蒜苗", "蒜黄", "百合", "山药豆",
            "菜",
        ),
        exclude=frozenset({"菜籽油", "菜油", "梅菜扣肉"}),
    ),
    # 谷薯主食（米/面/粉/薯 类；排在海鲜之后，避免 虾米→谷薯）
    Rule(
        "谷薯主食",
        contains=(
            "大米", "小米", "糯米", "黑米", "糙米", "薏米", "玉米", "米线", "米糕",
            "米饭", "炒饭", "烩饭", "煲仔饭", "面条", "挂面", "拉面", "刀削面",
            "米粉", "河粉", "肠粉", "粉丝", "粉条", "红薯粉", "凉皮", "面筋",
            "土豆", "红薯", "紫薯", "白薯", "木薯", "山药", "芋头", "年糕",
            "馒头", "饺子", "馄饨", "云吞", "粽子", "汤圆", "油条", "烧饼", "面包",
            "面粉", "米", "饭", "面", "粉", "薯",
        ),
        exclude=frozenset({"米酒", "米粉肉", "面筋串"}),
    ),
    # 水果
    Rule(
        "水果",
        contains=(
            "苹果", "香蕉", "葡萄", "西瓜", "草莓", "芒果", "橙子", "橘子", "桔子",
            "柚子", "柠檬", "菠萝", "猕猴桃", "火龙果", "樱桃", "车厘子", "蓝莓",
            "桑葚", "桃子", "杏", "李子", "荔枝", "龙眼", "桂圆", "杨梅", "榴莲",
            "山竹", "木瓜", "柿子", "石榴", "枇杷", "牛油果", "无花果", "山楂",
            "百香果", "哈密瓜", "甜瓜", "香瓜", "椰子", "梨", "枣",
            "果",
        ),
        exclude=frozenset({"果酱", "果冻", "果干", "坚果"}),
    ),
    # 乳品烘焙（牛奶/奶油/黄油/巧克力/烘焙料 等）
    Rule(
        "乳品烘焙",
        contains=(
            "牛奶", "酸奶", "淡奶油", "炼乳", "奶粉", "奶酪", "芝士", "起司",
            "奶油", "黄油", "巧克力", "可可粉", "吉利丁", "吉利粉", "低筋面粉",
            "高筋面粉", "中筋面粉", "蛋糕粉", "奥利奥", "奶",
        ),
        exclude=frozenset({"奶茶", "奶油饼干"}),
    ),
)


# ============================================================
# 调料规则
# ============================================================
SEASONING_RULES: Tuple[Rule, ...] = (
    # 去腥增香（鲜香辛料 + 酒类；洋葱/蒜苔/蒜苗等真实食材排除）
    Rule(
        "去腥增香",
        contains=(
            "料酒", "黄酒", "米酒", "醪糟", "酒酿", "花雕", "啤酒", "白酒", "红酒",
            "香葱", "小葱", "大葱", "葱花", "葱段", "姜", "蒜", "高汤", "陈皮",
        ),
        exclude=frozenset({
            "洋葱", "洋葱圈", "洋葱丝", "洋葱碎", "洋葱末", "洋葱丁",
            "紫洋葱", "白洋葱", "红洋葱", "黄洋葱",
            "蒜苔", "蒜薹", "蒜苗", "蒜黄", "蒜蓉酱", "蒜头",
        }),
    ),
    # 辣味调料（辣椒面/辣椒粉 归粉末调料，靠长关键词优先；不含裸「辣椒」，避免误捕食材）
    Rule(
        "辣味调料",
        contains=(
            "辣椒酱", "辣椒油", "油泼辣子", "火锅底料", "干辣椒", "小米辣", "泡椒",
            "剁椒", "麻辣", "辣酱", "辣",
        ),
        exclude=frozenset({"辣白菜", "辣条"}),
    ),
    # 香辛料（干香辛料；胡椒粉/五香粉等归粉末，靠长关键词优先）
    Rule(
        "香辛料",
        contains=(
            "花椒", "八角", "桂皮", "香叶", "丁香", "草果", "白芷", "甘草", "小茴香",
            "孜然", "沙姜", "山奈", "香茅", "紫苏", "迷迭香", "百里香", "罗勒", "牛至",
            "咖喱", "肉桂", "豆蔻", "砂仁", "大料", "五香", "十三香", "胡椒", "干姜",
        ),
    ),
    # 粉末调料（粉/面/苏打/发酵辅料；不设裸「粉」避免 粉丝/粉条 误伤）
    Rule(
        "粉末调料",
        contains=(
            "五香粉", "十三香", "胡椒粉", "花椒粉", "孜然粉", "辣椒粉", "辣椒面",
            "椒盐", "咖喱粉", "奥尔良腌料", "烧烤料", "淀粉", "生粉", "芡粉",
            "小苏打", "泡打粉", "酵母", "干桂花", "吉士粉", "盐焗粉",
        ),
    ),
    # 酱料
    Rule(
        "酱料",
        contains=(
            "豆瓣酱", "黄豆酱", "甜面酱", "番茄酱", "芝麻酱", "花生酱", "沙拉酱",
            "千岛酱", "蛋黄酱", "烧烤酱", "沙茶酱", "海鲜酱", "叉烧酱", "柱侯酱",
            "蒜蓉辣酱", "韩式辣酱", "老干妈", "腐乳", "南乳", "豆豉", "味噌", "虾酱",
            "鱼子酱", "果酱", "酱",
        ),
        exclude=frozenset({"酱牛肉", "酱骨头", "酱肉", "酱鸭", "酱鸡", "酱肘子", "酱香饼"}),
    ),
    # 基础调味（盐/糖/醋/酱油/味精 等；长关键词优先消解 酱油→基础 而非 酱料）
    Rule(
        "基础调味",
        contains=(
            "生抽", "老抽", "酱油", "味极鲜", "蚝油", "鱼露", "鸡精", "鸡粉", "鸡汁",
            "味精", "白糖", "冰糖", "糖粉", "蜂蜜", "麦芽糖", "糖浆", "白醋", "香醋",
            "陈醋", "米醋", "黑醋", "苹果醋", "盐", "糖", "醋",
        ),
        exclude=frozenset({"盐田虾", "盐焗鸡", "糖醋排骨", "糖醋里脊", "醋溜白菜"}),
    ),
    # 油脂（结尾「油」的油脂类，排除黄油/牛油/奶油/板油/淡奶油 等食材）
    Rule(
        "油脂",
        contains=(
            "食用油", "植物油", "调和油", "菜籽油", "花生油", "玉米油", "橄榄油",
            "葵花籽油", "猪油", "鸡油", "香油", "芝麻油", "花椒油", "葱油",
            "油",
        ),
        exclude=frozenset({
            "黄油", "牛油", "奶油", "板油", "淡奶油", "酱油", "蚝油", "鱼露",
            "油菜", "油麦菜", "油豆角", "油豆腐", "油条", "油饼", "油面筋", "油果",
        }),
    ),
)


# ============================================================
# 菜谱规则（特定类目在前；家常菜为兜底）
# ============================================================
RECIPE_RULES: Tuple[Rule, ...] = (
    Rule(
        "甜点",
        contains=(
            "蛋糕", "甜点", "甜品", "布丁", "冰淇淋", "雪糕", "蛋挞", "曲奇", "饼干",
            "面包", "吐司", "汤圆", "糖水", "月饼", "慕斯", "马卡龙", "泡芙",
            "杨枝甘露", "双皮奶", "奶昔", "布丁", "司康", "班戟", "千层",
        ),
    ),
    Rule(
        "面食",
        contains=(
            "面条", "挂面", "拉面", "刀削面", "凉面", "炒面", "汤面", "焖面",
            "米粉", "河粉", "凉皮", "年糕", "馒头", "包子", "饺子", "馄饨", "云吞",
            "烧饼", "馅饼", "春卷", "油条", "手抓饼", "葱油饼", "鸡蛋饼", "酱香饼",
            "面", "饼",
        ),
    ),
    Rule(
        "汤羹",
        contains=("汤", "羹", "粥", "煲汤", "炖汤", "浓汤", "清汤"),
    ),
    Rule(
        "炖菜",
        contains=("红烧", "炖", "焖", "卤", "煲", "烧肉", "扣肉"),
    ),
    Rule(
        "凉菜",
        contains=("凉拌", "凉菜", "沙拉", "拍黄瓜", "泡菜", "腌", "拌"),
    ),
    Rule(
        "减脂餐",
        contains=("减脂", "轻食", "低卡", "瘦身", "健身餐", "掉秤", "健康餐"),
    ),
    Rule(
        "快手菜",
        contains=("快手", "懒人", "简单", "快捷", "快速", "省时", "5分钟", "10分钟", "15分钟", "一锅"),
    ),
    Rule(
        "家常菜",
        contains=("家常",),
    ),
)


# ============================================================
# 匹配实现
# ============================================================

def _normalize(name: str) -> str:
    return (name or "").strip()


def _build_exact_index(rules: Tuple[Rule, ...]) -> Dict[str, str]:
    index: Dict[str, str] = {}
    for rule in rules:
        for exact_name in rule.exact:
            index.setdefault(exact_name, rule.category)
    return index


def _match(rules: Tuple[Rule, ...], exact_index: Dict[str, str], name: str) -> Optional[str]:
    """按 专名精确 → 子串（长关键词优先，同长时表序靠前优先）→ 排除保护 的顺序匹配。"""
    if name in exact_index:
        return exact_index[name]
    best_len = -1
    best_idx = -1
    for rule_index, rule in enumerate(rules):
        if name in rule.exclude:
            continue
        for kw in rule.contains:
            # 严格大于才更新：同长时保留先出现的规则（表序靠前优先）
            if kw in name and len(kw) > best_len:
                best_len = len(kw)
                best_idx = rule_index
    if best_idx < 0:
        return None
    return rules[best_idx].category


# 预构建专名索引
_INGREDIENT_EXACT = _build_exact_index(INGREDIENT_RULES)
_SEASONING_EXACT = _build_exact_index(SEASONING_RULES)
_RECIPE_EXACT = _build_exact_index(RECIPE_RULES)


def classify_ingredient(name: str, known_seasonings: Optional[set] = None) -> Optional[str]:
    """食材归类。识别为调料（is_seasoning）时返回 None。

    known_seasonings: 已存在的调料名集合，透传给 is_seasoning 兜底。
    注意：守卫只信任 is_seasoning 的边界（SEASONING_KEYWORDS + EXCLUSIONS），
    不叠加调料分类器——否则 辣椒/小米辣/油菜 等真实食材会被误判为调料。
    """
    name = _normalize(name)
    if not name:
        return None
    if is_seasoning(name, known_seasonings):
        return None
    return _match(INGREDIENT_RULES, _INGREDIENT_EXACT, name)


def classify_seasoning(name: str) -> Optional[str]:
    """调料归类。无法识别返回 None。"""
    name = _normalize(name)
    if not name:
        return None
    return _match(SEASONING_RULES, _SEASONING_EXACT, name)


def classify_recipe(title: str, ingredient_names: Optional[List[str]] = None) -> Optional[str]:
    """菜谱归类。初版仅按标题规则，未命中回落「家常菜」。

    ingredient_names 预留用于后续按主食材增强，当前未使用。
    """
    title = _normalize(title)
    if not title:
        return "家常菜"
    category = _match(RECIPE_RULES, _RECIPE_EXACT, title)
    if category is not None:
        return category
    return "家常菜"


def resolve_recipe_category(title: str, explicit: Optional[str] = None) -> str:
    """菜谱归类统一入口：显式 category（JSON 直入提供）优先，否则按标题规则。

    explicit 必须落在规范菜谱分类清单（RECIPE_CATEGORIES）内才被采用，
    否则视为不可信输入回落标题规则——防止拼写错误/非法值被落成新分类。
    显式值转 str 再比对，兼容 JSON 里 category 为数字/布尔等非字符串的情况。
    """
    if explicit:
        name = str(explicit or "").strip()
        if name in RECIPE_CATEGORIES:
            return name
    return classify_recipe(title)
