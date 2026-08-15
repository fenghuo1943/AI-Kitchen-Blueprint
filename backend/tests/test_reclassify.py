"""reclassify_defaults.py 存量清理脚本测试。

在 SQLite 内存库中预置"默认分类 + 调料误入食材 + 杂质 + 变体 + 默认菜谱"，
断言 build_plan 计数、apply_plan 的各阶段转换（调料迁移/杂质软删/变体合并/
食材与调料归类/菜谱链接 UPDATE），以及最关键的幂等性（二次 apply 为 no-op）。
"""
import uuid

import pytest

from app.db.models import (
    Ingredient, IngredientAlias, IngredientCategory,
    Recipe, RecipeCategory, RecipeCategoryLink,
    RecipeIngredient, RecipeSeasoning, Seasoning, SeasoningCategory,
)
from app.repositories.ingredient_repository import IngredientRepository
from scripts.reclassify_defaults import apply_plan, build_plan


def _mk_cat(db, model, name):
    cat = model(name=name)
    db.add(cat)
    db.flush()
    return cat


@pytest.fixture
def seeded(db_session):
    """构造存量脏数据：默认分类 + 调料误入食材 + 杂质 + 变体 + 默认菜谱。"""
    db = db_session
    ing_default = _mk_cat(db, IngredientCategory, "默认")
    sea_default = _mk_cat(db, SeasoningCategory, "默认")
    rec_default = _mk_cat(db, RecipeCategory, "默认")
    _mk_cat(db, IngredientCategory, "蔬菜")  # 预建，验证 get_or_create 复用

    def mk_ing(name):
        ing = Ingredient(id=str(uuid.uuid4()), canonical_name=name, category_id=ing_default.id)
        db.add(ing)
        db.flush()
        return ing

    def mk_recipe(title, cats, ingredients=()):
        recipe = Recipe(id=str(uuid.uuid4()), title=title, status="published")
        db.add(recipe)
        db.flush()
        for cid in cats:
            db.add(RecipeCategoryLink(id=str(uuid.uuid4()), recipe_id=recipe.id, category_id=cid))
        for ing, qty in ingredients:
            db.add(RecipeIngredient(id=str(uuid.uuid4()), recipe_id=recipe.id,
                                    ingredient_id=ing.id, quantity=qty, sort_order=0))
        db.flush()
        return recipe

    ginger = mk_ing("姜")
    water = mk_ing("水")
    potato = mk_ing("土豆")
    potato_variant = mk_ing("土豆（黄皮）")
    tomato = mk_ing("西红柿")

    mk_recipe("红烧肉", [rec_default.id], ingredients=[(ginger, "10克")])
    mk_recipe("土豆烧肉", [rec_default.id], ingredients=[(potato_variant, "2个")])
    mk_recipe("番茄炒蛋", [rec_default.id])
    # 带默认+非默认两个链接的菜谱，phase5 不应改动
    rec_home = _mk_cat(db, RecipeCategory, "家常菜")
    mk_recipe("番茄炒蛋2", [rec_default.id, rec_home.id])

    sea_soy = Seasoning(id=str(uuid.uuid4()), canonical_name="生抽", category_id=sea_default.id)
    db.add(sea_soy)
    db.flush()

    return {
        "db": db,
        "ginger": ginger, "water": water, "potato": potato,
        "potato_variant": potato_variant, "tomato": tomato, "sea_soy": sea_soy,
    }


def test_build_plan_counts(seeded):
    plan = build_plan(seeded["db"])
    s = plan["stages"]

    assert len(s["0_variant_merge"]["merged"]) == 1
    assert s["0_variant_merge"]["merged"][0]["name"] == "土豆（黄皮）"

    assert len(s["1_seasoning_migration"]["converted"]) == 1
    assert s["1_seasoning_migration"]["converted"][0]["name"] == "姜"
    assert len(s["1_seasoning_migration"]["converted"][0]["recipe_ingredient_ids"]) == 1

    assert len(s["2_impurities"]["deleted"]) == 1
    assert s["2_impurities"]["deleted"][0]["name"] == "水"

    # 姜/水/变体已由前序阶段处理，phase3 只剩 土豆/西红柿
    reclassified = {i["name"]: i["category"]
                    for i in s["3_ingredient_reclassify"]["reclassified"]}
    assert reclassified == {"土豆": "谷薯主食", "西红柿": "蔬菜"}

    assert len(s["4_seasoning_reclassify"]["reclassified"]) == 1
    assert s["4_seasoning_reclassify"]["reclassified"][0]["name"] == "生抽"

    # 番茄炒蛋 也只有默认链接 → 重归类为家常菜；番茄炒蛋2 有双链接 → 不在范围
    reclass_titles = {i["title"] for i in s["5_recipe_reclassify"]["reclassified"]}
    assert reclass_titles == {"红烧肉", "土豆烧肉", "番茄炒蛋"}


def test_apply_plan(seeded):
    db = seeded["db"]
    plan = build_plan(db)
    apply_plan(db, plan)

    # 阶段1 调料迁移：姜 软删，Seasoning 姜 创建，菜谱关联转为 recipe_seasonings
    assert seeded["ginger"].deleted_at is not None
    sea_ginger = db.query(Seasoning).filter(Seasoning.canonical_name == "姜").first()
    assert sea_ginger is not None
    assert sea_ginger.category_id is not None  # classify_seasoning 自动归类
    assert db.query(RecipeIngredient).filter(
        RecipeIngredient.ingredient_id == seeded["ginger"].id).count() == 0
    assert db.query(RecipeSeasoning).filter(
        RecipeSeasoning.seasoning_id == sea_ginger.id).count() == 1

    # 阶段2 杂质：水 软删
    assert seeded["water"].deleted_at is not None

    # 阶段0 变体合并：变体软删 + 引用改指 base + 写入别名
    assert seeded["potato_variant"].deleted_at is not None
    assert db.query(RecipeIngredient).filter(
        RecipeIngredient.ingredient_id == seeded["potato_variant"].id).count() == 0
    assert db.query(RecipeIngredient).filter(
        RecipeIngredient.ingredient_id == seeded["potato"].id).count() == 1
    assert db.query(IngredientAlias).filter(
        IngredientAlias.ingredient_id == seeded["potato"].id,
        IngredientAlias.alias == "土豆（黄皮）",
    ).count() == 1

    # 阶段3 食材归类
    repo = IngredientRepository(db)
    assert repo.get_category_name(seeded["tomato"].category_id) == "蔬菜"
    assert repo.get_category_name(seeded["potato"].category_id) == "谷薯主食"

    # 阶段4 调料归类
    scat = db.query(SeasoningCategory).filter(
        SeasoningCategory.id == seeded["sea_soy"].category_id).first()
    assert scat.name == "基础调味"

    # 阶段5 菜谱链接 UPDATE（红烧肉/土豆烧肉 → 炖菜；番茄炒蛋2 保持两个链接）
    for title in ("红烧肉", "土豆烧肉"):
        recipe = db.query(Recipe).filter(Recipe.title == title).first()
        links = db.query(RecipeCategoryLink).filter(
            RecipeCategoryLink.recipe_id == recipe.id).all()
        assert len(links) == 1
        rcat = db.query(RecipeCategory).filter(RecipeCategory.id == links[0].category_id).first()
        assert rcat.name == "炖菜"
    r2 = db.query(Recipe).filter(Recipe.title == "番茄炒蛋2").first()
    assert db.query(RecipeCategoryLink).filter(
        RecipeCategoryLink.recipe_id == r2.id).count() == 2


def test_idempotent(seeded):
    """幂等性最关键：二次 apply（等价于重跑）应为 no-op。"""
    db = seeded["db"]
    plan = build_plan(db)
    apply_plan(db, plan)

    plan2 = build_plan(db)
    for stage in plan2["stages"].values():
        for key, items in stage.items():
            assert not items, f"{key} 残留: {items}"
