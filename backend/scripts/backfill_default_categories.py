"""回填默认分类：把没有分类的菜谱/食材/调料设为「默认」分类。

背景：入库时未指定分类的菜谱/食材/调料现已统一落到默认分类
（app.repositories.category_repository.get_default_category_id，按名称'默认'解析）。
本脚本对历史数据做一次性回填，保证库中不再存在无分类记录。幂等可重跑。

执行：python scripts/backfill_default_categories.py
"""
import sys
from pathlib import Path

# 添加 backend 目录到 Python 路径
backend_dir = Path(__file__).parent.parent
sys.path.insert(0, str(backend_dir))

import uuid

from sqlalchemy.orm import Session

from app.db.database import get_session_local
from app.db.models import (
    Recipe, RecipeCategoryLink, Ingredient, Seasoning,
    RecipeCategory, IngredientCategory, SeasoningCategory,
)


def _default_category_id(db: Session, model, type_: str) -> str:
    """按名称'默认'解析该类型的默认分类ID（与 get_default_category_id 同规则）。"""
    cat = db.query(model).filter(model.name == "默认").first()
    if cat:
        return cat.id
    return "1"


def backfill(db: Session):
    # 默认分类ID（生产库为 UUID，测试/种子为 '1'）
    default_recipe_cat = _default_category_id(db, RecipeCategory, "recipe")
    default_ing_cat = _default_category_id(db, IngredientCategory, "ingredient")
    default_sea_cat = _default_category_id(db, SeasoningCategory, "seasoning")

    # 默认分类是否存在（不存在时插入会触发外键错误，提前预警）
    missing = []
    for name, cid in (("recipe", default_recipe_cat), ("ingredient", default_ing_cat), ("seasoning", default_sea_cat)):
        if name == "recipe":
            exists = db.query(RecipeCategory.id).filter(RecipeCategory.id == cid).first() is not None
        elif name == "ingredient":
            exists = db.query(IngredientCategory.id).filter(IngredientCategory.id == cid).first() is not None
        else:
            exists = db.query(SeasoningCategory.id).filter(SeasoningCategory.id == cid).first() is not None
        if not exists:
            missing.append(name)
    if missing:
        print(f"[警告] 默认分类(名称'默认'，id={ {'recipe': default_recipe_cat, 'ingredient': default_ing_cat, 'seasoning': default_sea_cat} })缺失：{missing}")
        print("       请先执行 migrations/002_add_cook_features.sql 或 seed 数据后再回填。")

    # 1) 菜谱：无任何分类关联 → 补默认分类关联
    no_cat_recipes = (
        db.query(Recipe.id)
        .outerjoin(RecipeCategoryLink, RecipeCategoryLink.recipe_id == Recipe.id)
        .filter(RecipeCategoryLink.id.is_(None))
        .all()
    )
    added_links = 0
    for (rid,) in no_cat_recipes:
        exists = db.query(RecipeCategoryLink.id).filter(
            RecipeCategoryLink.recipe_id == rid,
            RecipeCategoryLink.category_id == default_recipe_cat,
        ).first()
        if exists:
            continue
        db.add(RecipeCategoryLink(
            id=str(uuid.uuid4()),
            recipe_id=rid,
            category_id=default_recipe_cat,
        ))
        added_links += 1
    print(f"菜谱：{len(no_cat_recipes)} 个无分类 → 新增 {added_links} 条默认分类关联")

    # 2) 食材：category_id 为空 → 设为默认分类（category 字符串也为空时补 '默认'）
    ing_no_cat = (
        db.query(Ingredient.id, Ingredient.category)
        .filter(Ingredient.category_id.is_(None))
        .all()
    )
    ing_updated = 0
    for iid, cat_str in ing_no_cat:
        update = {"category_id": default_ing_cat}
        if not (cat_str or "").strip():
            update["category"] = "默认"
        db.query(Ingredient).filter(Ingredient.id == iid).update(update)
        ing_updated += 1
    print(f"食材：{len(ing_no_cat)} 个无分类 → 已设为默认分类")

    # 3) 调料：category_id 为空 → 设为默认分类
    sea_no_cat = (
        db.query(Seasoning.id)
        .filter(Seasoning.category_id.is_(None))
        .all()
    )
    for (sid,) in sea_no_cat:
        db.query(Seasoning).filter(Seasoning.id == sid).update({"category_id": default_sea_cat})
    print(f"调料：{len(sea_no_cat)} 个无分类 → 已设为默认分类")

    db.commit()
    print("回填完成。")


if __name__ == "__main__":
    db = get_session_local()()
    try:
        backfill(db)
    finally:
        db.close()
