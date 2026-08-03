"""从旧库 cookbook 迁移菜谱数据到当前库 cook

旧库 cookbook（Z-Blog cook 项目的 user_* 表结构）内含用户烽火1943 录入的
18 道菜谱，本次迁移到当前 AI 家庭厨房助手生产库 cook：
  - 菜谱本体：菜谱 / 分类 / 食材 / 调料 / 各关联表
  - 不迁移：历史 / 每日菜单 / 收藏（用户确认只迁菜谱本体）
  - 补充：仅 4 道明显不完整的菜（水饺 / 西红柿炒鸡蛋步骤 / 冒菜 / 奥尔良鸡肉包），
    其余 14 道忠实迁移不改动

用法：
  python scripts/migrate_from_cookbook.py          # 执行迁移
  python scripts/migrate_from_cookbook.py --dry-run # 只打印计划，不落库
"""
import sys
import uuid
from pathlib import Path
from datetime import datetime

# 添加 backend 目录到 Python 路径
backend_dir = Path(__file__).parent.parent
sys.path.insert(0, str(backend_dir))

import pymysql
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.pinyin import to_pinyin
from app.db.database import get_session_local
from app.db.models import (
    Ingredient, Seasoning, Recipe, RecipeSource, RecipeIngredient,
    RecipeStep, RecipeSeasoning, RecipeCategoryLink,
    IngredientCategory, SeasoningCategory, RecipeCategory,
)

# 迁移标记：写进 created_by / 作者，同时作为幂等保护
CREATED_BY = "烽火1943"
SOURCE_DB = "cookbook"

# ---------------------------------------------------------------------------
# 补充内容：仅 4 道缺内容的菜。其余菜谱忠实迁移，不做任何改动。
# 数据来源：2026-08-03 联网检索的家常标准做法（小红书/百科/搜狐等菜谱教程）。
# ---------------------------------------------------------------------------
ENRICH = {
    # 水饺：源库中完全为空（无食材/调料/步骤），仅有分类“面食”
    8: {
        "summary": "皮薄馅大的猪肉大葱水饺，家常做法，鲜香多汁",
        "cook_minutes": 60,
        "ingredients": [("面粉", "500g"), ("猪肉", "500g"), ("大葱", "200g")],
        "seasonings": [
            ("盐", "适量"), ("生抽", "2勺"), ("老抽", "1勺"), ("蚝油", "1勺"),
            ("糖", "少许"), ("胡椒粉", "少许"), ("香油", "2勺"), ("花椒", "15粒"),
        ],
        "steps": [
            "面粉加盐，分次倒入温水（约30℃），搅成絮状后揉成光滑面团，盖保鲜膜醒发30分钟",
            "花椒加葱姜用开水冲泡20分钟，滤出花椒水晾凉备用",
            "猪肉（3肥7瘦）剁成肉馅，加盐、生抽、老抽、蚝油、糖、白胡椒粉，朝一个方向搅打上劲",
            "分3次加入花椒水，每次等完全吸收后再加，最后淋香油拌匀",
            "大葱切碎先用香油拌匀（防止出水），包之前再与肉馅轻轻翻拌均匀",
            "面团搓长条切小剂子，擀成中间厚边缘薄的圆皮，包入馅料对折捏紧收口",
            "水烧开下饺子，用勺背轻推防粘，沸腾后点冷水3次，饺子浮起鼓肚即可捞出",
        ],
    },
    # 西红柿炒鸡蛋：缺步骤，补步骤 + 顺带补糖/葱花两道常规调料
    1: {
        "extra_seasonings": [("糖", "半勺"), ("葱花", "适量")],
        "steps": [
            "西红柿顶部划十字，开水烫10秒去皮，切成小块；鸡蛋打散加少许盐",
            "热锅倒油，倒入蛋液炒成大块蛋絮，半熟盛出备用",
            "锅留底油，倒入西红柿中火翻炒，用铲子轻压出汁，加少许盐和糖",
            "倒入炒好的鸡蛋快速翻拌，让蛋块裹满汤汁，撒葱花出锅",
        ],
    },
    # 冒菜：缺食材和调料（步骤已有，步骤里提到牛肉/豆瓣酱/火锅底料/辣椒面等）
    10: {
        "ingredients": [
            ("牛肉", "300g"), ("土豆", "1个"), ("藕", "1节"), ("豆皮", "1张"),
            ("金针菇", "1把"), ("豆芽", "1把"), ("午餐肉", "半盒"),
        ],
        "seasonings": [
            ("生抽", "2勺"), ("蚝油", "1勺"), ("料酒", "1勺"), ("胡椒粉", "少许"),
            ("豆瓣酱", "1勺"), ("火锅底料", "1块"), ("辣椒面", "适量"), ("糖", "少许"),
            ("盐", "适量"), ("葱花", "适量"), ("蒜", "适量"), ("姜", "适量"),
        ],
    },
    # 奥尔良鸡肉包：缺调料（食材/步骤已有，步骤提到奥尔良腌料/生抽/蚝油）
    16: {
        "seasonings": [
            ("奥尔良腌料", "18g"), ("生抽", "1勺"), ("蚝油", "1勺"),
            ("盐", "适量"), ("糖", "少许"), ("酵母", "3g"),
        ],
    },
}

# 补充新增食材/调料所属分类（源库分类名；若目标已存在同名则复用）
NEW_ING_CATEGORY = {
    "大葱": "蔬菜", "藕": "蔬菜", "豆皮": "蔬菜",
    "金针菇": "蔬菜", "豆芽": "蔬菜", "午餐肉": "肉类",
}
NEW_SEASONING_CATEGORY = {
    "火锅底料": "辣味调料", "辣椒面": "辣味调料",
    "香油": "基础调味", "奥尔良腌料": "粉末调料", "酵母": "粉末调料",
}


def generate_uuid() -> str:
    return str(uuid.uuid4())


def read_source(conn) -> dict:
    """读取旧库 cookbook 全部相关数据，按源 id 组织为 dict"""
    cur = conn.cursor(pymysql.cursors.DictCursor)

    def rows(table, order="id"):
        cur.execute(f"SELECT * FROM {SOURCE_DB}.{table} ORDER BY {order}")
        return cur.fetchall()

    data = {
        "recipes": rows("user_recipes"),
        "recipe_categories": rows("user_categories"),
        "recipe_category_links": rows("user_recipe_categories"),
        "ing_categories": rows("user_ing_categories"),
        "ingredients": rows("user_ingredients"),
        "recipe_ingredients": rows("user_recipe_ingredients"),
        "seasoning_categories": rows("user_seasoning_categories"),
        "seasonings": rows("user_seasonings"),
        "recipe_seasonings": rows("user_recipe_seasonings"),
        "steps": rows("user_steps", "recipe_id, step_order"),
    }
    return data


def get_or_create_ingredient(db, name, category_id, by_name) -> Ingredient:
    """按名称取食材，不存在则创建（补充的新食材走这里）"""
    ing = by_name.get(name)
    if ing is None:
        ing = Ingredient(
            id=generate_uuid(),
            canonical_name=name,
            pinyin=to_pinyin(name),
            category_id=category_id,
            confidence_status="verified",
        )
        db.add(ing)
        by_name[name] = ing
    return ing


def get_or_create_seasoning(db, name, category_id, by_name) -> Seasoning:
    """按名称取调料，不存在则创建"""
    sea = by_name.get(name)
    if sea is None:
        sea = Seasoning(
            id=generate_uuid(),
            canonical_name=name,
            pinyin=to_pinyin(name),
            category_id=category_id,
        )
        db.add(sea)
        by_name[name] = sea
    return sea


def migrate(db: Session, data: dict) -> dict:
    """执行迁移，返回统计信息"""
    stats = {
        "recipes": 0, "recipe_categories": 0, "ing_categories": 0,
        "seasoning_categories": 0, "ingredients": 0, "seasonings": 0,
        "recipe_ingredients": 0, "recipe_seasonings": 0, "steps": 0,
        "category_links": 0, "sources": 0,
    }

    # ---- 1. 菜谱分类（recipe_categories）----
    old_cat2new = {}
    for i, c in enumerate(data["recipe_categories"], start=1):
        obj = RecipeCategory(
            id=generate_uuid(), name=c["name"],
            parent_id=None, sort_order=i,
            created_at=c.get("created_at"), updated_at=c.get("updated_at"),
        )
        db.add(obj)
        old_cat2new[c["id"]] = obj
        stats["recipe_categories"] += 1

    # ---- 2. 食材分类（ingredient_categories）----
    old_ing_cat2new = {}
    ing_cat_by_name = {}
    for c in data["ing_categories"]:
        obj = IngredientCategory(
            id=generate_uuid(), name=c["name"],
            created_at=c.get("created_at"), updated_at=c.get("updated_at"),
        )
        db.add(obj)
        old_ing_cat2new[c["id"]] = obj
        ing_cat_by_name[c["name"]] = obj
        stats["ing_categories"] += 1

    # ---- 3. 调料分类（seasoning_categories）----
    old_sea_cat2new = {}
    sea_cat_by_name = {}
    for c in data["seasoning_categories"]:
        obj = SeasoningCategory(
            id=generate_uuid(), name=c["name"],
            created_at=c.get("created_at"), updated_at=c.get("updated_at"),
        )
        db.add(obj)
        old_sea_cat2new[c["id"]] = obj
        sea_cat_by_name[c["name"]] = obj
        stats["seasoning_categories"] += 1

    # 先落库分类，保证后续食材/调料的 category_id 外键有效
    db.flush()

    # ---- 4. 食材（ingredients）----
    old_ing2new = {}   # 源食材 id -> Ingredient
    ing_by_name = {}   # 名称 -> Ingredient
    for ing in data["ingredients"]:
        obj = Ingredient(
            id=generate_uuid(),
            canonical_name=ing["name"],
            pinyin=ing["pinyin"],
            category_id=old_ing_cat2new.get(ing["category_id"]).id
            if old_ing_cat2new.get(ing["category_id"]) else None,
            confidence_status="verified",
            created_at=ing.get("created_at"), updated_at=ing.get("updated_at"),
        )
        db.add(obj)
        old_ing2new[ing["id"]] = obj
        ing_by_name[ing["name"]] = obj
        stats["ingredients"] += 1

    # 补充食材（新名称先 get-or-create）
    for src_id, enrich in ENRICH.items():
        for name, _qty in enrich.get("ingredients", []):
            cat_obj = ing_cat_by_name.get(NEW_ING_CATEGORY.get(name, "蔬菜"))
            get_or_create_ingredient(db, name, cat_obj.id if cat_obj else None, ing_by_name)

    # ---- 5. 调料（seasonings）----
    old_sea2new = {}
    sea_by_name = {}
    for sea in data["seasonings"]:
        obj = Seasoning(
            id=generate_uuid(),
            canonical_name=sea["name"],
            pinyin=sea["pinyin"],
            category_id=old_sea_cat2new.get(sea["category_id"]).id
            if old_sea_cat2new.get(sea["category_id"]) else None,
            created_at=sea.get("created_at"), updated_at=sea.get("updated_at"),
        )
        db.add(obj)
        old_sea2new[sea["id"]] = obj
        sea_by_name[sea["name"]] = obj
        stats["seasonings"] += 1

    for src_id, enrich in ENRICH.items():
        for name, _qty in enrich.get("seasonings", []) + enrich.get("extra_seasonings", []):
            cat_obj = sea_cat_by_name.get(NEW_SEASONING_CATEGORY.get(name, "基础调味"))
            get_or_create_seasoning(db, name, cat_obj.id if cat_obj else None, sea_by_name)

    # 统计含补充新增的食材/调料（by_name 已含源数据 + 补充）
    stats["ingredients"] = len(ing_by_name)
    stats["seasonings"] = len(sea_by_name)

    # 落库食材/调料，供菜谱关联表引用
    db.flush()

    # ---- 6. 来源标记 + 菜谱本体 ----
    source = RecipeSource(
        id=generate_uuid(),
        source_type="manual",
        source_url=f"{SOURCE_DB}://user_recipes",
        author=CREATED_BY,
        license="user_data",
        fetched_at=datetime.utcnow(),
    )
    db.add(source)
    stats["sources"] += 1

    old_recipe2new = {}
    recipe_ings = {}
    recipe_seas = {}
    recipe_steps = {}
    for src in data["recipes"]:
        src_id = src["id"]
        enrich = ENRICH.get(src_id, {})
        recipe = Recipe(
            id=generate_uuid(),
            title=src["title"],
            pinyin=src["pinyin"],
            summary=(enrich.get("summary") if "summary" in enrich
                     else (src["description"].strip() or None)),
            cover=src["cover"],
            servings=None,
            prep_minutes=None,
            cook_minutes=enrich.get("cook_minutes", src["cook_time"]),
            difficulty=None,
            source_id=source.id,
            status="published",
            revision=1,
            created_by=CREATED_BY,
            created_at=src.get("created_at"), updated_at=src.get("updated_at"),
        )
        db.add(recipe)
        old_recipe2new[src_id] = recipe
        stats["recipes"] += 1

        # 食材（源数据 + 补充，按顺序解析为对象）
        ing_list = []
        for ri in data["recipe_ingredients"]:
            if ri["recipe_id"] == src_id:
                ing_list.append((old_ing2new[ri["ingredient_id"]], ri.get("quantity") or ""))
        for name, qty in enrich.get("ingredients", []):
            ing_list.append((ing_by_name[name], qty))
        recipe_ings[src_id] = ing_list

        # 调料（源数据 + 补充）
        sea_list = []
        for rs in data["recipe_seasonings"]:
            if rs["recipe_id"] == src_id:
                sea_list.append((old_sea2new[rs["seasoning_id"]], rs.get("quantity") or ""))
        for name, qty in enrich.get("seasonings", []) + enrich.get("extra_seasonings", []):
            sea_list.append((sea_by_name[name], qty))
        recipe_seas[src_id] = sea_list

        # 步骤（补充优先，否则用源数据）
        steps = []
        if "steps" in enrich:
            steps = [(no, text, None) for no, text in enumerate(enrich["steps"], start=1)]
        else:
            for st in data["steps"]:
                if st["recipe_id"] == src_id:
                    steps.append((st["step_order"], st["content"], st.get("image")))
        recipe_steps[src_id] = steps

    # 落库菜谱本体，供各关联表引用
    db.flush()

    # ---- 7. 关联表 ----
    for src_id, recipe in old_recipe2new.items():
        # 菜谱-食材
        for sort, (ing_obj, quantity) in enumerate(recipe_ings[src_id]):
            ri = RecipeIngredient(
                id=generate_uuid(), recipe_id=recipe.id,
                ingredient_id=ing_obj.id, quantity=quantity or None,
                raw_quantity=quantity or None, preparation=None,
                optional=0, sort_order=sort,
            )
            db.add(ri)
            stats["recipe_ingredients"] += 1

        # 菜谱-调料
        for sea_obj, quantity in recipe_seas[src_id]:
            rs = RecipeSeasoning(
                id=generate_uuid(), recipe_id=recipe.id,
                seasoning_id=sea_obj.id, quantity=quantity or None,
            )
            db.add(rs)
            stats["recipe_seasonings"] += 1

        # 步骤
        for step_no, content, image in recipe_steps[src_id]:
            st = RecipeStep(
                id=generate_uuid(), recipe_id=recipe.id,
                step_no=step_no, instruction=content, image_url=image,
            )
            db.add(st)
            stats["steps"] += 1

        # 菜谱-分类
        for link in data["recipe_category_links"]:
            if link["recipe_id"] == src_id:
                cl = RecipeCategoryLink(
                    id=generate_uuid(), recipe_id=recipe.id,
                    category_id=old_cat2new[link["category_id"]].id,
                    created_at=link.get("created_at"), updated_at=link.get("updated_at"),
                )
                db.add(cl)
                stats["category_links"] += 1

    return stats


def main():
    import argparse
    parser = argparse.ArgumentParser(description="从 cookbook 迁移菜谱到 cook")
    parser.add_argument("--dry-run", action="store_true", help="只打印计划，不落库")
    args = parser.parse_args()

    # 1. 读源库
    conn = pymysql.connect(
        host=settings.DB_HOST, port=settings.DB_PORT,
        user=settings.DB_USER, password=settings.DB_PASSWORD,
        charset="utf8mb4", connect_timeout=10,
    )
    data = read_source(conn)
    conn.close()
    print(f"源库 {SOURCE_DB} 读取完成："
          f"菜谱 {len(data['recipes'])} 道，"
          f"食材 {len(data['ingredients'])} 个，"
          f"调料 {len(data['seasonings'])} 个")

    # 2. 幂等保护
    db = get_session_local()()
    try:
        exists = db.query(Recipe).filter(Recipe.created_by == CREATED_BY).first()
        if exists and not args.dry_run:
            print(f"检测到目标库已有 {CREATED_BY} 的菜谱（id={exists.id}），已迁移过，中止。"
                  f"如需强制重跑请先清理。")
            return

        stats = migrate(db, data)
        if args.dry_run:
            db.rollback()
            print("\n[dry-run] 仅预览，未落库。计划插入：")
        else:
            db.commit()
            print("\n迁移完成，已写入 cook 库：")
        for k, v in stats.items():
            print(f"  {k:20s} {v}")
    finally:
        db.close()


if __name__ == "__main__":
    main()
