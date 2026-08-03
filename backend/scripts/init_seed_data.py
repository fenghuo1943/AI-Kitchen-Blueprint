"""初始化种子数据"""
import sys
from pathlib import Path

# 添加 backend 目录到 Python 路径
backend_dir = Path(__file__).parent.parent
sys.path.insert(0, str(backend_dir))

import json
import uuid
from datetime import datetime
from sqlalchemy.orm import Session
from pypinyin import lazy_pinyin
from app.db.database import get_session_local, init_db
from app.db.models import (
    Household, Ingredient, IngredientAlias, Tag,
    Recipe, RecipeSource, RecipeIngredient, RecipeStep, RecipeTag,
    IngredientCategory, SeasoningCategory, Seasoning, RecipeSeasoning,
    RecipeCategory, RecipeCategoryLink
)


def generate_uuid() -> str:
    return str(uuid.uuid4())


def to_pinyin(text: str) -> str:
    """生成无空格拼音（用于拼音搜索）"""
    if not text:
        return ""
    return "".join(lazy_pinyin(text))


def seed_data(db: Session):
    """初始化种子数据"""

    # 创建测试家庭
    household = Household(
        id=generate_uuid(),
        name="测试家庭",
        description="用于开发测试的家庭"
    )
    db.add(household)

    # 创建默认分类（防止引用空分类）
    default_ing_category = IngredientCategory(id="1", name="默认")
    default_sea_category = SeasoningCategory(id="1", name="默认")
    default_recipe_category = RecipeCategory(id="1", name="默认", sort_order=0)
    db.add_all([default_ing_category, default_sea_category, default_recipe_category])

    # 食材分类（name -> obj）
    ing_categories = {}
    for name in ["蔬菜", "肉类", "蛋类", "主食", "豆制品", "水产", "菌菇"]:
        cat = IngredientCategory(id=generate_uuid(), name=name)
        db.add(cat)
        ing_categories[name] = cat

    # 菜谱分类
    recipe_categories = {}
    for i, name in enumerate(["家常菜", "快手菜", "汤羹", "主食", "凉拌"], 1):
        cat = RecipeCategory(id=generate_uuid(), name=name, sort_order=i)
        db.add(cat)
        recipe_categories[name] = cat

    # 调料分类 + 基础调料
    sea_categories = {}
    for name in ["基础调料", "酱料", "香料"]:
        cat = SeasoningCategory(id=generate_uuid(), name=name)
        db.add(cat)
        sea_categories[name] = cat

    seasonings_data = [
        {"canonical_name": "盐", "category": "基础调料"},
        {"canonical_name": "糖", "category": "基础调料"},
        {"canonical_name": "酱油", "category": "酱料"},
        {"canonical_name": "料酒", "category": "酱料"},
        {"canonical_name": "食用油", "category": "基础调料"},
        {"canonical_name": "醋", "category": "酱料"},
        {"canonical_name": "葱", "category": "香料"},
        {"canonical_name": "姜", "category": "香料"},
        {"canonical_name": "蒜", "category": "香料"},
    ]
    seasoning_objects = {}
    for data in seasonings_data:
        seasoning = Seasoning(
            id=generate_uuid(),
            canonical_name=data["canonical_name"],
            pinyin=to_pinyin(data["canonical_name"]),
            category_id=sea_categories[data["category"]].id,
        )
        db.add(seasoning)
        seasoning_objects[data["canonical_name"]] = seasoning

    # 创建基础食材（带分类与拼音）
    ingredients_data = [
        {"canonical_name": "鸡蛋", "category": "蛋类", "season_months": json.dumps(["1","2","3","4","5","6","7","8","9","10","11","12"]), "allergens": json.dumps(["eggs"])},
        {"canonical_name": "番茄", "category": "蔬菜", "season_months": json.dumps(["5","6","7","8","9"]), "allergens": json.dumps([])},
        {"canonical_name": "土豆", "category": "蔬菜", "season_months": json.dumps(["1","2","3","4","5","6","7","8","9","10","11","12"]), "allergens": json.dumps([])},
        {"canonical_name": "米饭", "category": "主食", "season_months": json.dumps(["1","2","3","4","5","6","7","8","9","10","11","12"]), "allergens": json.dumps(["gluten"])},
        {"canonical_name": "猪肉", "category": "肉类", "season_months": json.dumps(["1","2","3","4","5","6","7","8","9","10","11","12"]), "allergens": json.dumps([])},
        {"canonical_name": "青椒", "category": "蔬菜", "season_months": json.dumps(["5","6","7","8","9"]), "allergens": json.dumps([])},
        {"canonical_name": "豆腐", "category": "豆制品", "season_months": json.dumps(["1","2","3","4","5","6","7","8","9","10","11","12"]), "allergens": json.dumps(["soy"])},
        {"canonical_name": "白菜", "category": "蔬菜", "season_months": json.dumps(["10","11","12","1","2","3"]), "allergens": json.dumps([])},
        {"canonical_name": "胡萝卜", "category": "蔬菜", "season_months": json.dumps(["1","2","3","4","5","6","7","8","9","10","11","12"]), "allergens": json.dumps([])},
        {"canonical_name": "洋葱", "category": "蔬菜", "season_months": json.dumps(["1","2","3","4","5","6","7","8","9","10","11","12"]), "allergens": json.dumps([])},
    ]

    ingredient_objects = {}
    for data in ingredients_data:
        cat_obj = ing_categories.get(data["category"])
        ingredient = Ingredient(
            id=generate_uuid(),
            **data,
            pinyin=to_pinyin(data["canonical_name"]),
            category_id=cat_obj.id if cat_obj else None,
        )
        db.add(ingredient)
        ingredient_objects[data["canonical_name"]] = ingredient

    # 创建食材别名
    aliases_data = [
        {"ingredient": "鸡蛋", "aliases": ["蛋", "鸡子"]},
        {"ingredient": "番茄", "aliases": ["西红柿", "洋柿子"]},
        {"ingredient": "土豆", "aliases": ["马铃薯", "洋芋"]},
        {"ingredient": "猪肉", "aliases": ["肉", "五花肉", "里脊肉"]},
    ]

    for data in aliases_data:
        ingredient = ingredient_objects[data["ingredient"]]
        for alias in data["aliases"]:
            alias_obj = IngredientAlias(
                id=generate_uuid(),
                ingredient_id=ingredient.id,
                alias=alias
            )
            db.add(alias_obj)

    # 创建标签
    tags_data = [
        {"name": "家常菜", "type": "cuisine", "description": "家常风味"},
        {"name": "川菜", "type": "cuisine", "description": "四川风味"},
        {"name": "粤菜", "type": "cuisine", "description": "广东风味"},
        {"name": "快炒", "type": "equipment", "description": "适合炒锅"},
        {"name": "炖煮", "type": "equipment", "description": "适合炖锅"},
        {"name": "简单", "type": "goal", "description": "制作简单"},
        {"name": "15分钟", "type": "goal", "description": "快速制作"},
        {"name": "冬季", "type": "season", "description": "适合冬季"},
        {"name": "夏季", "type": "season", "description": "适合夏季"},
        {"name": "清淡", "type": "flavor", "description": "口味清淡"},
        {"name": "微辣", "type": "flavor", "description": "微辣口味"},
    ]

    tag_objects = {}
    for data in tags_data:
        tag = Tag(id=generate_uuid(), **data)
        db.add(tag)
        tag_objects[f"{data['name']}_{data['type']}"] = tag

    # 创建示例菜谱
    recipes_data = [
        {
            "title": "番茄炒蛋",
            "summary": "经典的家常菜，简单易做，营养丰富",
            "servings": 2,
            "prep_minutes": 5,
            "cook_minutes": 10,
            "difficulty": "简单",
            "ingredients": [
                {"name": "番茄", "quantity": "2", "unit": "个"},
                {"name": "鸡蛋", "quantity": "3", "unit": "个"},
                {"name": "葱", "quantity": "适量", "unit": ""},
            ],
            "steps": [
                {"instruction": "番茄洗净切块，鸡蛋打散加少许盐搅匀", "duration_minutes": 2},
                {"instruction": "热锅倒油，倒入蛋液炒至凝固盛出", "duration_minutes": 2},
                {"instruction": "锅中留底油，放入番茄块翻炒出汁", "duration_minutes": 3},
                {"instruction": "倒入炒好的鸡蛋，加盐调味，翻炒均匀即可", "duration_minutes": 2},
            ],
            "tags": ["家常菜", "快炒", "简单", "15分钟"],
            "categories": ["家常菜", "快手菜"],
            "seasonings": [{"name": "盐", "quantity": "适量"}, {"name": "葱", "quantity": "适量"}],
        },
        {
            "title": "土豆烧肉",
            "summary": "软糯入味，下饭神器",
            "servings": 3,
            "prep_minutes": 10,
            "cook_minutes": 30,
            "difficulty": "中等",
            "ingredients": [
                {"name": "土豆", "quantity": "2", "unit": "个"},
                {"name": "猪肉", "quantity": "300", "unit": "克"},
                {"name": "胡萝卜", "quantity": "1", "unit": "个"},
                {"name": "葱", "quantity": "适量", "unit": ""},
                {"name": "姜", "quantity": "适量", "unit": ""},
            ],
            "steps": [
                {"instruction": "土豆、胡萝卜去皮切块，猪肉切块焯水", "duration_minutes": 5},
                {"instruction": "热锅倒油，放入肉块煸炒出油", "duration_minutes": 5},
                {"instruction": "加入葱姜爆香，倒入料酒、酱油调味", "duration_minutes": 2},
                {"instruction": "加入土豆、胡萝卜块，加水没过食材", "duration_minutes": 2},
                {"instruction": "大火烧开后转小火炖煮25分钟至软烂", "duration_minutes": 25},
            ],
            "tags": ["家常菜", "炖煮", "冬季"],
            "categories": ["家常菜"],
            "seasonings": [{"name": "酱油", "quantity": "适量"}, {"name": "料酒", "quantity": "适量"}, {"name": "姜", "quantity": "适量"}],
        },
    ]

    for recipe_data in recipes_data:
        recipe_id = generate_uuid()
        recipe = Recipe(
            id=recipe_id,
            title=recipe_data["title"],
            pinyin=to_pinyin(recipe_data["title"]),
            summary=recipe_data["summary"],
            servings=recipe_data["servings"],
            prep_minutes=recipe_data["prep_minutes"],
            cook_minutes=recipe_data["cook_minutes"],
            difficulty=recipe_data["difficulty"],
            status="published",
            created_by="system"
        )
        db.add(recipe)

        # 添加食材
        for i, ing_data in enumerate(recipe_data["ingredients"]):
            ingredient = ingredient_objects.get(ing_data["name"])
            if ingredient:
                recipe_ingredient = RecipeIngredient(
                    id=generate_uuid(),
                    recipe_id=recipe_id,
                    ingredient_id=ingredient.id,
                    quantity=ing_data["quantity"],
                    unit=ing_data["unit"],
                    sort_order=i
                )
                db.add(recipe_ingredient)

        # 添加步骤
        for i, step_data in enumerate(recipe_data["steps"], 1):
            step = RecipeStep(
                id=generate_uuid(),
                recipe_id=recipe_id,
                step_no=i,
                instruction=step_data["instruction"],
                duration_minutes=step_data.get("duration_minutes")
            )
            db.add(step)

        # 添加标签
        for tag_name in recipe_data["tags"]:
            tag = tag_objects.get(f"{tag_name}_cuisine") or tag_objects.get(f"{tag_name}_equipment") or tag_objects.get(f"{tag_name}_goal") or tag_objects.get(f"{tag_name}_season")
            if tag:
                recipe_tag = RecipeTag(
                    id=generate_uuid(),
                    recipe_id=recipe_id,
                    tag_id=tag.id
                )
                db.add(recipe_tag)

        # 添加菜谱分类关联
        for cat_name in recipe_data.get("categories", []):
            cat = recipe_categories.get(cat_name)
            if cat:
                db.add(RecipeCategoryLink(
                    id=generate_uuid(),
                    recipe_id=recipe_id,
                    category_id=cat.id
                ))

        # 添加调料关联
        for sea_data in recipe_data.get("seasonings", []):
            seasoning = seasoning_objects.get(sea_data["name"])
            if seasoning:
                db.add(RecipeSeasoning(
                    id=generate_uuid(),
                    recipe_id=recipe_id,
                    seasoning_id=seasoning.id,
                    quantity=sea_data.get("quantity"),
                ))

    db.commit()
    print("种子数据初始化完成！")


if __name__ == "__main__":
    print("开始初始化数据库...")
    init_db()
    print("数据库表创建完成，开始插入种子数据...")
    db = get_session_local()()
    try:
        seed_data(db)
    finally:
        db.close()
