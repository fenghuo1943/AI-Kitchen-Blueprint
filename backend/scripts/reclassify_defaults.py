"""存量分类重归类：把仍处「默认」分类的历史数据按规则分类器重新归类。

背景：入库管线此前从不产出分类，历史数据大量落入「默认」分类，且混入
调料（姜/蒜/料酒/生抽…）与杂质（水/清水/油）。本脚本为一次性存量清理，
默认只做 dry-run（打印计划、不改库），确认无误后 --apply 单事务执行。

用法：
    python scripts/reclassify_defaults.py                        # dry-run，打印计划
    python scripts/reclassify_defaults.py --apply                # 单事务执行并提交
    python scripts/reclassify_defaults.py --report out.json      # 计划导出 JSON
    python scripts/reclassify_defaults.py --apply --report out.json

阶段（每阶段只处理"当前仍处默认 / 仍活跃且符合条件"的对象，天然幂等）：
  0 变体合并：土豆（黄皮）→土豆；歧义（鸡精或味精）报告需人工
  1 默认食材中的调料迁入 seasonings（recipe_ingredients → recipe_seasonings，
    数量取 raw_quantity or quantity+unit；被库存引用则保留食材行）
  2 杂质（水/清水/油…）无引用软删，有引用报告跳过
  3 剩余默认食材按 classify_ingredient 归类（自动建新分类）
  4 默认调料按 classify_seasoning 归类
  5 默认菜谱（链接集恰为 {默认}）按 classify_recipe 归类（UPDATE 原链接）

幂等：plan 由当前库状态计算，apply 只执行 plan；二次运行 plan 应为空。
"""
import argparse
import json
import re
import sys
import uuid
from datetime import datetime
from pathlib import Path

# 添加 backend 目录到 Python 路径
backend_dir = Path(__file__).parent.parent
sys.path.insert(0, str(backend_dir))

from sqlalchemy import func, or_
from sqlalchemy.orm import Session

from app.core.category_classifier import (
    classify_ingredient, classify_seasoning, classify_recipe,
)
from app.core.pinyin import to_pinyin
from app.core.seasoning_classifier import is_seasoning
from app.db.database import get_session_local
from app.db.models import (
    Ingredient, IngredientAlias, InventoryItem,
    Recipe, RecipeCategoryLink, RecipeIngredient, RecipeSeasoning, Seasoning,
)
from app.repositories.category_repository import (
    get_default_category_id, get_or_create_category_id,
)

# 阶段2 杂质名单：这些"食材"实为过程性用物，无引用则清理
IMPURITIES = frozenset({"水", "清水", "油", "热水", "温水", "冷水", "凉水", "开水"})


def _now() -> datetime:
    return datetime.utcnow()


def _variant_base(name: str):
    """土豆（黄皮）→ '土豆'；含『或』的歧义名（鸡精或味精）→ None；否则 None。"""
    name = (name or "").strip()
    if not name or "或" in name:
        return None
    m = re.match(r"^(?P<base>.+?)[（(][^（）()]{1,10}[)）]$", name)
    if m:
        base = m.group("base").strip()
        if base and base != name:
            return base
    return None


def build_plan(db: Session) -> dict:
    """纯读：由当前库状态计算清理计划（不产生任何写操作）。"""
    defaults = {
        "recipe": get_default_category_id(db, "recipe"),
        "ingredient": get_default_category_id(db, "ingredient"),
        "seasoning": get_default_category_id(db, "seasoning"),
    }
    stages = {
        "0_variant_merge": {"merged": [], "renamed": [], "skipped": [], "needs_human": []},
        "1_seasoning_migration": {"converted": [], "skipped": []},
        "2_impurities": {"deleted": [], "skipped": []},
        "3_ingredient_reclassify": {"reclassified": [], "unidentified": []},
        "4_seasoning_reclassify": {"reclassified": [], "unidentified": []},
        "5_recipe_reclassify": {"reclassified": [], "skipped": []},
    }

    # ---- 阶段0 变体合并 ----
    active_ings = db.query(Ingredient).filter(Ingredient.deleted_at.is_(None)).all()
    for ing in active_ings:
        base = _variant_base(ing.canonical_name)
        if base is None:
            if "或" in ing.canonical_name:
                stages["0_variant_merge"]["needs_human"].append({
                    "id": ing.id, "name": ing.canonical_name, "reason": "歧义变体（含『或』）",
                })
            continue
        base_ing = db.query(Ingredient).filter(Ingredient.canonical_name == base).first()
        if base_ing is not None and base_ing.deleted_at is None:
            stages["0_variant_merge"]["merged"].append({
                "id": ing.id, "name": ing.canonical_name, "base_id": base_ing.id, "base_name": base,
            })
        elif base_ing is None:
            stages["0_variant_merge"]["renamed"].append({
                "id": ing.id, "name": ing.canonical_name, "new_name": base,
            })
        else:
            stages["0_variant_merge"]["needs_human"].append({
                "id": ing.id, "name": ing.canonical_name, "reason": f"目标名「{base}」被软删记录占用",
            })

    # ---- 阶段1/2/3 共用的"默认+活跃"食材集合 ----
    default_ing_ids = [defaults["ingredient"]]
    default_ings = (
        db.query(Ingredient)
        .filter(
            Ingredient.deleted_at.is_(None),
            or_(Ingredient.category_id.in_(default_ing_ids), Ingredient.category_id.is_(None)),
        )
        .all()
    )
    inv_count = {iid: n for iid, n in db.query(
        InventoryItem.ingredient_id, func.count(InventoryItem.id)
    ).group_by(InventoryItem.ingredient_id).all()}
    ri_count = {iid: n for iid, n in db.query(
        RecipeIngredient.ingredient_id, func.count(RecipeIngredient.id)
    ).group_by(RecipeIngredient.ingredient_id).all()}

    # 已由前序阶段处理的食材，阶段3 不再重复归类（一个对象只出现在一个阶段）。
    # 仅合并（已软删）/迁移（调料）/杂质（软删）排除；改名的不排除——
    # 改名后的食材（如 辣椒(红、尖)→辣椒）仍需走阶段3 自动归类。
    handled_ids = {item["id"] for item in stages["0_variant_merge"]["merged"]}
    handled_ids |= {item["ingredient_id"] for item in stages["1_seasoning_migration"]["converted"]}
    handled_ids |= {item["id"] for item in stages["2_impurities"]["deleted"]}

    for ing in default_ings:
        name = ing.canonical_name
        refs = (inv_count.get(ing.id, 0) or 0) + (ri_count.get(ing.id, 0) or 0)

        # 阶段1：调料迁移
        if is_seasoning(name):
            ri_rows = db.query(RecipeIngredient.id).filter(
                RecipeIngredient.ingredient_id == ing.id).all()
            stages["1_seasoning_migration"]["converted"].append({
                "ingredient_id": ing.id, "name": name,
                "recipe_ingredient_ids": [r.id for r in ri_rows],
                "kept_ingredient": bool(inv_count.get(ing.id, 0)),
            })
            continue

        # 阶段2：杂质清理
        if name in IMPURITIES:
            if refs:
                stages["2_impurities"]["skipped"].append({
                    "id": ing.id, "name": name, "reason": f"被 {refs} 处引用",
                })
            else:
                stages["2_impurities"]["deleted"].append({"id": ing.id, "name": name})
            continue

        # 阶段3：剩余默认食材归类（跳过前序阶段已处理的）
        if ing.id in handled_ids:
            continue
        cat = classify_ingredient(name)
        if cat:
            stages["3_ingredient_reclassify"]["reclassified"].append({
                "id": ing.id, "name": name, "category": cat,
            })
        else:
            stages["3_ingredient_reclassify"]["unidentified"].append({
                "id": ing.id, "name": name,
            })

    # ---- 阶段4 默认调料归类 ----
    default_sea_ids = [defaults["seasoning"]]
    default_seas = (
        db.query(Seasoning)
        .filter(
            Seasoning.deleted_at.is_(None),
            or_(Seasoning.category_id.in_(default_sea_ids), Seasoning.category_id.is_(None)),
        )
        .all()
    )
    for sea in default_seas:
        cat = classify_seasoning(sea.canonical_name)
        if cat:
            stages["4_seasoning_reclassify"]["reclassified"].append({
                "id": sea.id, "name": sea.canonical_name, "category": cat,
            })
        else:
            stages["4_seasoning_reclassify"]["unidentified"].append({
                "id": sea.id, "name": sea.canonical_name,
            })

    # ---- 阶段5 默认菜谱归类（链接集恰为 {默认}）----
    links_by_recipe = {}
    for link in db.query(RecipeCategoryLink).all():
        links_by_recipe.setdefault(link.recipe_id, []).append((link.category_id, link.id))
    for rid, pairs in links_by_recipe.items():
        cat_ids = {cid for cid, _ in pairs}
        if defaults["recipe"] not in cat_ids or len(cat_ids) != 1:
            continue
        recipe = db.query(Recipe.title).filter(
            Recipe.id == rid, Recipe.deleted_at.is_(None)).first()
        if not recipe:
            continue
        link_id = pairs[0][1]  # 唯一链接即默认链接
        stages["5_recipe_reclassify"]["reclassified"].append({
            "recipe_id": rid, "title": recipe.title, "category": classify_recipe(recipe.title),
            "link_id": link_id,
        })

    return {"stages": stages}


def _find_or_create_seasoning(db: Session, name: str) -> Seasoning:
    """按名称复用调料；软删同名复活；不存在则创建（自动归类）。"""
    sea = db.query(Seasoning).filter(Seasoning.canonical_name == name).first()
    if sea:
        if sea.deleted_at is not None:
            sea.deleted_at = None
            db.flush()
        return sea
    sea_cat = classify_seasoning(name)
    sea = Seasoning(
        id=str(uuid.uuid4()),
        canonical_name=name,
        pinyin=to_pinyin(name),
        category_id=get_or_create_category_id(db, "seasoning", sea_cat) if sea_cat else None,
    )
    db.add(sea)
    db.flush()
    return sea


def apply_plan(db: Session, plan: dict):
    """执行计划（调用方负责 commit；幂等：plan 来自 build_plan 快照）。"""
    stages = plan["stages"]

    # 阶段0 变体合并
    for item in stages["0_variant_merge"]["merged"]:
        variant = db.query(Ingredient).filter(Ingredient.id == item["id"]).first()
        base = db.query(Ingredient).filter(Ingredient.id == item["base_id"]).first()
        if not variant or not base:
            continue
        for ri in db.query(RecipeIngredient).filter(
                RecipeIngredient.ingredient_id == variant.id).all():
            conflict = db.query(RecipeIngredient.id).filter(
                RecipeIngredient.recipe_id == ri.recipe_id,
                RecipeIngredient.ingredient_id == base.id,
                RecipeIngredient.sort_order == ri.sort_order,
            ).first()
            if conflict:
                continue
            ri.ingredient_id = base.id
        db.query(InventoryItem).filter(InventoryItem.ingredient_id == variant.id).update(
            {"ingredient_id": base.id}, synchronize_session=False)
        if not db.query(IngredientAlias.id).filter(
                IngredientAlias.alias == variant.canonical_name).first():
            db.add(IngredientAlias(
                id=str(uuid.uuid4()), ingredient_id=base.id, alias=variant.canonical_name))
        variant.deleted_at = _now()
    for item in stages["0_variant_merge"]["renamed"]:
        ing = db.query(Ingredient).filter(Ingredient.id == item["id"]).first()
        if ing:
            ing.canonical_name = item["new_name"]
            ing.pinyin = to_pinyin(item["new_name"])

    # 阶段1 调料迁移
    for item in stages["1_seasoning_migration"]["converted"]:
        ing = db.query(Ingredient).filter(Ingredient.id == item["ingredient_id"]).first()
        if not ing:
            continue
        sea = _find_or_create_seasoning(db, ing.canonical_name)
        for ri_id in item["recipe_ingredient_ids"]:
            ri = db.query(RecipeIngredient).filter(RecipeIngredient.id == ri_id).first()
            if not ri:
                continue
            if db.query(RecipeSeasoning.id).filter(
                    RecipeSeasoning.recipe_id == ri.recipe_id,
                    RecipeSeasoning.seasoning_id == sea.id,
            ).first():
                continue
            qty = ri.raw_quantity or (f"{ri.quantity}{ri.unit or ''}" if ri.quantity else None)
            db.add(RecipeSeasoning(
                id=str(uuid.uuid4()), recipe_id=ri.recipe_id,
                seasoning_id=sea.id, quantity=qty))
            db.delete(ri)
        if not item["kept_ingredient"]:
            ing.deleted_at = _now()

    # 阶段2 杂质清理
    for item in stages["2_impurities"]["deleted"]:
        ing = db.query(Ingredient).filter(Ingredient.id == item["id"]).first()
        if ing:
            ing.deleted_at = _now()

    # 阶段3 剩余默认食材归类
    for item in stages["3_ingredient_reclassify"]["reclassified"]:
        ing = db.query(Ingredient).filter(Ingredient.id == item["id"]).first()
        if ing:
            cid = get_or_create_category_id(db, "ingredient", item["category"])
            ing.category_id = cid

    # 阶段4 默认调料归类
    for item in stages["4_seasoning_reclassify"]["reclassified"]:
        sea = db.query(Seasoning).filter(Seasoning.id == item["id"]).first()
        if sea:
            sea.category_id = get_or_create_category_id(db, "seasoning", item["category"])

    # 阶段5 默认菜谱归类（UPDATE 原默认链接，避免 delete+insert 唯一冲突）
    for item in stages["5_recipe_reclassify"]["reclassified"]:
        link = db.query(RecipeCategoryLink).filter(
            RecipeCategoryLink.id == item["link_id"]).first()
        if link:
            cid = get_or_create_category_id(db, "recipe", item["category"])
            if cid != link.category_id:
                link.category_id = cid


def _counts(stage: dict) -> str:
    """形如  merged=3 renamed=1 needs_human=2 的紧凑摘要。"""
    return "  ".join(f"{k}={len(v)}" for k, v in stage.items() if isinstance(v, list))


def print_plan(plan: dict, title: str = "重归类计划（dry-run，未写库）"):
    stages = plan["stages"]
    print("=" * 68)
    print(title)
    print("=" * 68)

    print(f"\n[阶段0] 变体合并\n        {_counts(stages['0_variant_merge'])}")
    for item in stages["0_variant_merge"]["merged"]:
        print(f"  合并  {item['name']}  → {item['base_name']}")
    for item in stages["0_variant_merge"]["renamed"]:
        print(f"  改名  {item['name']}  → {item['new_name']}")
    for item in stages["0_variant_merge"]["needs_human"]:
        print(f"  [需人工] {item['name']}（{item['reason']}）")

    print(f"\n[阶段1] 默认食材中的调料迁移到 seasonings\n        {_counts(stages['1_seasoning_migration'])}")
    for item in stages["1_seasoning_migration"]["converted"]:
        kept = "（保留食材行，被库存引用）" if item["kept_ingredient"] else ""
        print(f"  迁移  {item['name']}：{len(item['recipe_ingredient_ids'])} 处菜谱引用{kept}")

    print(f"\n[阶段2] 杂质清理\n        {_counts(stages['2_impurities'])}")
    for item in stages["2_impurities"]["deleted"]:
        print(f"  软删  {item['name']}")
    for item in stages["2_impurities"]["skipped"]:
        print(f"  [跳过] {item['name']}（{item['reason']}）")

    print(f"\n[阶段3] 剩余默认食材归类\n        {_counts(stages['3_ingredient_reclassify'])}")
    for item in stages["3_ingredient_reclassify"]["reclassified"]:
        print(f"  {item['name']}  → {item['category']}")
    for item in stages["3_ingredient_reclassify"]["unidentified"]:
        print(f"  [未识别，保持默认] {item['name']}")

    print(f"\n[阶段4] 默认调料归类\n        {_counts(stages['4_seasoning_reclassify'])}")
    for item in stages["4_seasoning_reclassify"]["reclassified"]:
        print(f"  {item['name']}  → {item['category']}")
    for item in stages["4_seasoning_reclassify"]["unidentified"]:
        print(f"  [未识别，保持默认] {item['name']}")

    print(f"\n[阶段5] 默认菜谱归类\n        {_counts(stages['5_recipe_reclassify'])}")
    for item in stages["5_recipe_reclassify"]["reclassified"]:
        print(f"  《{item['title']}》  → {item['category']}")


def main():
    parser = argparse.ArgumentParser(description="存量分类重归类（dry-run 默认）")
    parser.add_argument("--apply", action="store_true", help="执行写库并提交（默认仅打印计划）")
    parser.add_argument("--report", metavar="PATH", help="计划导出 JSON 路径")
    args = parser.parse_args()

    db = get_session_local()()
    try:
        plan = build_plan(db)
        if args.report:
            Path(args.report).write_text(
                json.dumps(plan, ensure_ascii=False, indent=2), encoding="utf-8")
            print(f"计划已导出: {args.report}\n")
        print_plan(plan)
        if args.apply:
            apply_plan(db, plan)
            db.commit()
            residual = build_plan(db)
            print("\n[apply] 已执行并提交。残量检查（二次 build_plan，应基本为空）：")
            print_plan(residual, title="残量计划")
    finally:
        db.close()


if __name__ == "__main__":
    main()
