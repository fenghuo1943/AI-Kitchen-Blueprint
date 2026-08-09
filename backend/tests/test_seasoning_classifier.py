"""调料/食材分类器单元测试。"""
import pytest

from app.core.seasoning_classifier import (
    SEASONING_EXCLUSIONS,
    is_seasoning,
    split_ingredients,
)

# (名字, 期望: True=调料 / False=食材)
CASES = [
    # 基础调味
    ("盐", True), ("食盐", True), ("海盐", True), ("椒盐", True),
    ("白糖", True), ("冰糖", True), ("红糖", True), ("糖霜", True), ("蜂蜜", True),
    ("陈醋", True), ("香醋", True), ("白醋", True),
    ("味精", True), ("鸡精", True), ("鸡粉", True),
    # 酱油/酒类
    ("生抽", True), ("老抽", True), ("酱油", True), ("蒸鱼豉油", True),
    ("味极鲜", True), ("蚝油", True), ("鱼露", True),
    ("料酒", True), ("黄酒", True), ("米酒", True),
    # 酱料
    ("豆瓣酱", True), ("甜面酱", True), ("番茄酱", True), ("辣椒酱", True),
    ("芝麻酱", True), ("老干妈", True), ("腐乳", True), ("豆豉", True),
    # 香料 / 香辛料
    ("花椒", True), ("花椒粉", True), ("八角", True), ("桂皮", True),
    ("香叶", True), ("孜然", True), ("五香粉", True), ("十三香", True),
    ("咖喱粉", True), ("咖喱块", True), ("胡椒粉", True),
    # 葱姜蒜（本系统约定为香料/调料）
    ("葱", True), ("香葱", True), ("葱花", True), ("姜", True), ("生姜", True),
    ("蒜", True), ("大蒜", True), ("蒜蓉", True),
    # 油脂类（结尾"油"）
    ("食用油", True), ("花生油", True), ("橄榄油", True), ("菜籽油", True),
    ("香油", True), ("芝麻油", True), ("猪油", True), ("辣椒油", True),
    # 淀粉 / 干辣椒 / 发酵辅料
    ("淀粉", True), ("玉米淀粉", True), ("生粉", True), ("小苏打", True),
    ("泡打粉", True), ("酵母", True), ("干辣椒", True), ("辣椒粉", True),
    ("辣椒面", True), ("泡椒", True), ("剁椒", True),
    # ---- 以下应为食材（False）----
    ("西红柿", False), ("鸡蛋", False), ("猪肉", False), ("牛肉", False),
    ("土豆", False), ("白菜", False), ("洋葱", False), ("青椒", False),
    ("辣椒", False), ("胡萝卜", False), ("豆腐", False), ("香菇", False),
    ("香肠", False), ("香干", False), ("面粉", False), ("糯米粉", False),
    ("牛油果", False), ("黄油", False), ("牛油", False), ("奶油", False),
    ("蒜苔", False), ("蒜苗", False), ("蒜黄", False), ("虾皮", False),
    ("花生", False), ("芝麻", False), ("腰果", False), ("虾仁", False),
    ("鱿鱼", False), ("皮蛋", False), ("咸鸭蛋", False), ("酱牛肉", False),
    ("豆皮", False), ("腐竹", False), ("年糕", False),
]


@pytest.mark.parametrize("name,expected", CASES)
def test_is_seasoning(name, expected):
    assert is_seasoning(name) is expected, f"{name!r} 分类错误"


def test_is_seasoning_empty():
    assert is_seasoning("") is False
    assert is_seasoning(None) is False
    assert is_seasoning("  ") is False


def test_is_seasoning_known_set_overrides_static_dict():
    # 用户手工维护在调料表的"鱼籽酱"（静态词典未覆盖）→ 精确命中 known 集合即为调料
    assert is_seasoning("鱼籽酱", {"鱼籽酱"}) is True
    # 静态词典已判定为调料的不受影响
    assert is_seasoning("盐") is True


def test_split_ingredients():
    ingredients = [
        {"name": "西红柿", "quantity": "2"},
        {"name": "盐", "quantity": "1"},
        {"name": "鸡蛋"},
        {"name": "生抽", "amount": "1勺"},
    ]
    real, seasonings = split_ingredients(ingredients)
    assert [i["name"] for i in real] == ["西红柿", "鸡蛋"]
    assert [s["name"] for s in seasonings] == ["盐", "生抽"]
    # 字段保留
    assert seasonings[1]["amount"] == "1勺"


def test_split_ingredients_blank_skipped():
    real, seasonings = split_ingredients([{"name": "  "}, {"name": None}, {"name": "盐"}])
    assert real == []
    assert [s["name"] for s in seasonings] == ["盐"]
