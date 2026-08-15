"""菜谱数据访问层"""
from datetime import date
from collections import defaultdict
from typing import Optional, List, Tuple
from sqlalchemy.orm import Session
from sqlalchemy import or_, and_, case, func, select, distinct, literal

from app.db.models import (
    Recipe, Ingredient, RecipeIngredient, RecipeStep, RecipeTag, Tag,
    RecipeCategory, RecipeCategoryLink, RecipeSeasoning, Seasoning,
    Favorite, RecipeHistory, MealPlan,
    IngestionCandidate, IngestionJob,
)


class RecipeRepository:
    """菜谱仓储类"""

    def __init__(self, db: Session):
        self.db = db

    def get_by_id(self, recipe_id: str) -> Optional[Recipe]:
        """根据ID获取菜谱"""
        return self.db.query(Recipe).filter(
            Recipe.id == recipe_id,
            Recipe.deleted_at.is_(None)
        ).first()

    def search(
        self,
        query: Optional[str] = None,
        status: Optional[str] = None,
        difficulty: Optional[str] = None,
        tags: Optional[List[str]] = None,
        max_cook_time: Optional[int] = None,
        ingredient_ids: Optional[List[str]] = None,
        match_mode: str = "any",
        category_id: Optional[str] = None,
        household_id: Optional[str] = None,
        sort: str = "score",
        order: str = "desc",
        deleted: bool = False,
        page: int = 1,
        page_size: int = 20
    ) -> Tuple[List[Recipe], int]:
        """搜索菜谱（支持食材/分类/关键词/拼音/排序/回收站，参考 cook RecipeSearchRepository）

        返回的 Recipe 对象附带瞬态属性：
        _score / _total_score / _is_favorited / _cooked_count / _is_in_today_menu / _category_ids
        """
        # ---- 过滤条件 ----
        conditions = [
            Recipe.deleted_at.isnot(None) if deleted else Recipe.deleted_at.is_(None)
        ]
        # 默认列表不展示 review（AI 采集待审候选），确认入库（published）后才出现在菜谱库
        if status is None:
            conditions.append(Recipe.status != "review")

        # 关键词：title / summary / 拼音前缀 / 分类名 / 食材名
        if query:
            keyword = query.strip()
            if keyword:
                conditions.append(or_(
                    Recipe.title.like(f"%{keyword}%"),
                    Recipe.summary.like(f"%{keyword}%"),
                    Recipe.pinyin.like(f"{keyword}%"),
                    self._category_name_match(keyword),
                    self._ingredient_name_match(keyword),
                ))

        if status:
            conditions.append(Recipe.status == status)
        if difficulty:
            conditions.append(Recipe.difficulty == difficulty)
        if max_cook_time is not None:
            conditions.append(
                (func.ifnull(Recipe.cook_minutes, 0) + func.ifnull(Recipe.prep_minutes, 0)) <= max_cook_time
            )
        # 标签
        if tags:
            conditions.append(Recipe.id.in_(
                select(RecipeTag.recipe_id).where(
                    and_(RecipeTag.tag_id == Tag.id, Tag.name.in_(tags))
                )
            ))
        # 食材：exact=同时包含全部，any=包含任一
        if ingredient_ids:
            ing_count_sub = select(func.count(distinct(RecipeIngredient.ingredient_id))).where(
                and_(
                    RecipeIngredient.recipe_id == Recipe.id,
                    RecipeIngredient.ingredient_id.in_(ingredient_ids),
                )
            ).scalar_subquery()
            if match_mode == "exact":
                conditions.append(ing_count_sub == len(ingredient_ids))
            else:
                conditions.append(ing_count_sub > 0)
        # 菜谱分类
        if category_id:
            conditions.append(Recipe.id.in_(
                select(RecipeCategoryLink.recipe_id).where(
                    RecipeCategoryLink.category_id == category_id
                )
            ))

        base = and_(*conditions)

        # ---- 计数 ----
        total = self.db.query(func.count(Recipe.id)).filter(base).scalar()

        # ---- 关键词评分（title×6 + 分类×2 + 食材×2 + summary×2 + 拼音前缀×1）----
        score_expr: object = literal(0)
        if query:
            keyword = query.strip()
            if keyword:
                score_expr = (
                    case((Recipe.title.like(f"%{keyword}%"), 6), else_=0)
                    + case((self._category_name_match(keyword), 2), else_=0)
                    + case((self._ingredient_name_match(keyword), 2), else_=0)
                    + case((Recipe.summary.like(f"%{keyword}%"), 2), else_=0)
                    + case((Recipe.pinyin.like(f"{keyword}%"), 1), else_=0)
                )

        # ---- 用户相关子查询（收藏/做过次数/今日菜单）----
        cooked_count_sub = None
        is_fav_sub = None
        if household_id:
            cooked_count_sub = select(func.count(MealPlan.id)).where(
                and_(MealPlan.recipe_id == Recipe.id, MealPlan.household_id == household_id)
            ).scalar_subquery()
            is_fav_sub = select(func.count(Favorite.id)).where(
                and_(Favorite.recipe_id == Recipe.id, Favorite.household_id == household_id)
            ).scalar_subquery()

        # total_score = score + cooked_count×0.5 + 收藏×2
        total_score_expr = score_expr
        if cooked_count_sub is not None:
            total_score_expr = total_score_expr + (cooked_count_sub * 0.5) + (is_fav_sub * 2)

        # total_score 是否真实表达式（有关键词或家庭偏好加分），否则是常量 literal(0)
        has_real_score = bool(query and query.strip()) or (cooked_count_sub is not None)

        # ---- 查询列表 ----
        stmt = self.db.query(Recipe, total_score_expr.label("total_score")).filter(base)

        order = order.lower()
        if sort == "date":
            stmt = stmt.order_by(Recipe.created_at.desc())
        elif sort == "title":
            stmt = stmt.order_by(Recipe.pinyin.asc(), Recipe.created_at.desc())
        elif sort == "cook" and cooked_count_sub is not None:
            stmt = stmt.order_by(cooked_count_sub.desc(), Recipe.created_at.desc())
        elif sort == "random":
            stmt = stmt.order_by(self._random_expr())
        else:  # score / 默认（综合评分）
            if has_real_score:
                expr = total_score_expr.asc() if order == "asc" else total_score_expr.desc()
                stmt = stmt.order_by(expr, Recipe.created_at.desc())
            else:
                # 无关键词且无家庭偏好数据：total_score 是常量，直接按创建时间排序
                stmt = stmt.order_by(Recipe.created_at.desc())

        offset = (page - 1) * page_size
        rows = stmt.offset(offset).limit(page_size).all()

        # ---- 结果装配（瞬态属性）----
        recipes: List[Recipe] = []
        for recipe, total_score in rows:
            recipe._total_score = float(total_score or 0)
            recipe._score = float(recipe._total_score)
            recipe._is_favorited = False
            recipe._cooked_count = 0
            recipe._is_in_today_menu = False
            recipes.append(recipe)

        if recipes and household_id:
            recipe_ids = [r.id for r in recipes]
            # 收藏
            fav_ids = set()
            for fav_id, in self.db.query(Favorite.recipe_id).filter(
                and_(Favorite.household_id == household_id, Favorite.recipe_id.in_(recipe_ids))
            ).all():
                fav_ids.add(fav_id)
            # 做过次数
            cooked_map = defaultdict(int)
            for rid, cnt in self.db.query(MealPlan.recipe_id, func.count(MealPlan.id)).filter(
                and_(MealPlan.household_id == household_id, MealPlan.recipe_id.in_(recipe_ids))
            ).group_by(MealPlan.recipe_id).all():
                cooked_map[rid] = cnt
            # 今日菜单
            today_ids = set()
            for rid, in self.db.query(MealPlan.recipe_id).filter(
                and_(
                    MealPlan.household_id == household_id,
                    MealPlan.recipe_id.in_(recipe_ids),
                    MealPlan.target_date == date.today().isoformat(),
                )
            ).all():
                today_ids.add(rid)
            for recipe in recipes:
                recipe._is_favorited = recipe.id in fav_ids
                recipe._cooked_count = cooked_map.get(recipe.id, 0)
                recipe._is_in_today_menu = recipe.id in today_ids

        # 分类ID
        if recipes:
            cat_map = defaultdict(list)
            for rid, cid in self.db.query(RecipeCategoryLink.recipe_id, RecipeCategoryLink.category_id).filter(
                RecipeCategoryLink.recipe_id.in_([r.id for r in recipes])
            ).all():
                cat_map[rid].append(cid)
            for recipe in recipes:
                recipe._category_ids = cat_map.get(recipe.id, [])

        return recipes, total

    @staticmethod
    def _category_name_match(keyword: str):
        """关键词命中菜谱分类名的 EXISTS 表达式"""
        return select(RecipeCategoryLink.id).where(
            and_(
                RecipeCategoryLink.recipe_id == Recipe.id,
                RecipeCategory.id == RecipeCategoryLink.category_id,
                RecipeCategory.name.like(f"%{keyword}%"),
            )
        ).exists()

    @staticmethod
    def _ingredient_name_match(keyword: str):
        """关键词命中菜谱所含食材名的 EXISTS 表达式"""
        return select(RecipeIngredient.id).where(
            and_(
                RecipeIngredient.recipe_id == Recipe.id,
                Ingredient.id == RecipeIngredient.ingredient_id,
                Ingredient.canonical_name.like(f"%{keyword}%"),
            )
        ).exists()

    def _random_expr(self):
        """随机排序表达式（兼容 SQLite/MySQL）"""
        dialect = self.db.get_bind().dialect.name
        return func.random() if dialect == "sqlite" else func.rand()

    def get_by_id_any(self, recipe_id: str) -> Optional[Recipe]:
        """根据ID获取菜谱（不区分软删状态，回收站详情用）"""
        return self.db.query(Recipe).filter(Recipe.id == recipe_id).first()

    def restore(self, recipe_id: str) -> Optional[Recipe]:
        """恢复软删除的菜谱"""
        recipe = self.get_by_id_any(recipe_id)
        if not recipe:
            return None
        recipe.deleted_at = None
        self.db.commit()
        self.db.refresh(recipe)
        return recipe

    def hard_delete(self, recipe_id: str) -> bool:
        """彻底删除菜谱（级联清理关联数据）"""
        recipe = self.get_by_id_any(recipe_id)
        if not recipe:
            return False
        # AI 采集关联表对 recipes(id) 未建 ON DELETE CASCADE，需显式清理：
        # - 候选本体：本菜谱即 review 候选，删除候选行
        # - 补全目标/任务结果：目标已被删除，置空避免外键残留
        self.db.query(IngestionCandidate).filter(
            IngestionCandidate.recipe_id == recipe_id
        ).delete(synchronize_session=False)
        self.db.query(IngestionCandidate).filter(
            IngestionCandidate.target_recipe_id == recipe_id
        ).update({IngestionCandidate.target_recipe_id: None}, synchronize_session=False)
        self.db.query(IngestionJob).filter(
            IngestionJob.result_recipe_id == recipe_id
        ).update({IngestionJob.result_recipe_id: None}, synchronize_session=False)
        self.db.query(IngestionJob).filter(
            IngestionJob.target_recipe_id == recipe_id
        ).update({IngestionJob.target_recipe_id: None}, synchronize_session=False)
        self.db.delete(recipe)
        self.db.commit()
        return True

    def create(self, recipe: Recipe) -> Recipe:
        """创建菜谱"""
        self.db.add(recipe)
        self.db.commit()
        self.db.refresh(recipe)
        return recipe

    def update(self, recipe: Recipe) -> Recipe:
        """更新菜谱"""
        self.db.commit()
        self.db.refresh(recipe)
        return recipe

    def soft_delete(self, recipe_id: str) -> bool:
        """软删除菜谱"""
        recipe = self.get_by_id(recipe_id)
        if not recipe:
            return False
        from datetime import datetime
        recipe.deleted_at = datetime.utcnow()
        self.db.commit()
        return True

    def add_ingredient(self, recipe_ingredient: RecipeIngredient) -> RecipeIngredient:
        """添加菜谱食材"""
        self.db.add(recipe_ingredient)
        self.db.commit()
        self.db.refresh(recipe_ingredient)
        return recipe_ingredient

    def remove_ingredients(self, recipe_id: str) -> None:
        """删除菜谱的所有食材"""
        self.db.query(RecipeIngredient).filter(
            RecipeIngredient.recipe_id == recipe_id
        ).delete()
        self.db.commit()

    def get_ingredients(self, recipe_id: str) -> List[RecipeIngredient]:
        """获取菜谱食材"""
        return self.db.query(RecipeIngredient).filter(
            RecipeIngredient.recipe_id == recipe_id
        ).order_by(RecipeIngredient.sort_order).all()

    def add_step(self, recipe_step: RecipeStep) -> RecipeStep:
        """添加菜谱步骤"""
        self.db.add(recipe_step)
        self.db.commit()
        self.db.refresh(recipe_step)
        return recipe_step

    def remove_steps(self, recipe_id: str) -> None:
        """删除菜谱的所有步骤"""
        self.db.query(RecipeStep).filter(
            RecipeStep.recipe_id == recipe_id
        ).delete()
        self.db.commit()

    def get_steps(self, recipe_id: str) -> List[RecipeStep]:
        """获取菜谱步骤"""
        return self.db.query(RecipeStep).filter(
            RecipeStep.recipe_id == recipe_id
        ).order_by(RecipeStep.step_no).all()

    def add_tags(self, recipe_id: str, tag_names: List[str]) -> None:
        """添加菜谱标签"""
        for tag_name in tag_names:
            # 查找或创建标签
            tag = self.db.query(Tag).filter(Tag.name == tag_name).first()
            if not tag:
                tag = Tag(name=tag_name, type="cuisine")
                self.db.add(tag)
                self.db.flush()

            # 创建关联
            recipe_tag = RecipeTag(recipe_id=recipe_id, tag_id=tag.id)
            self.db.add(recipe_tag)
        self.db.commit()

    def remove_tags(self, recipe_id: str) -> None:
        """删除菜谱的所有标签"""
        self.db.query(RecipeTag).filter(
            RecipeTag.recipe_id == recipe_id
        ).delete()
        self.db.commit()

    def get_tags(self, recipe_id: str) -> List[Tag]:
        """获取菜谱标签"""
        return self.db.query(Tag).join(RecipeTag).filter(
            RecipeTag.recipe_id == recipe_id
        ).all()

    # ---- 菜谱分类关联 ----
    def remove_categories(self, recipe_id: str) -> None:
        """删除菜谱的所有分类关联"""
        self.db.query(RecipeCategoryLink).filter(
            RecipeCategoryLink.recipe_id == recipe_id
        ).delete()
        self.db.commit()

    def add_category(self, recipe_id: str, category_id: str) -> None:
        """添加菜谱分类关联"""
        link = RecipeCategoryLink(
            recipe_id=recipe_id,
            category_id=category_id,
        )
        self.db.add(link)
        self.db.commit()

    def get_categories(self, recipe_id: str) -> List[RecipeCategory]:
        """获取菜谱的分类"""
        return self.db.query(RecipeCategory).join(RecipeCategoryLink).filter(
            RecipeCategoryLink.recipe_id == recipe_id
        ).all()

    def get_category_ids(self, recipe_id: str) -> List[str]:
        """获取菜谱分类ID列表"""
        return [row[0] for row in self.db.query(RecipeCategoryLink.category_id).filter(
            RecipeCategoryLink.recipe_id == recipe_id
        ).all()]

    # ---- 菜谱调料关联 ----
    def remove_seasonings(self, recipe_id: str) -> None:
        """删除菜谱的所有调料关联"""
        self.db.query(RecipeSeasoning).filter(
            RecipeSeasoning.recipe_id == recipe_id
        ).delete()
        self.db.commit()

    def add_seasoning(self, recipe_id: str, seasoning_id: str, quantity: Optional[str] = None) -> None:
        """添加菜谱调料关联"""
        link = RecipeSeasoning(
            recipe_id=recipe_id,
            seasoning_id=seasoning_id,
            quantity=quantity,
        )
        self.db.add(link)
        self.db.commit()

    def get_seasonings(self, recipe_id: str) -> List[RecipeSeasoning]:
        """获取菜谱的调料（含调料名）"""
        return self.db.query(RecipeSeasoning).filter(
            RecipeSeasoning.recipe_id == recipe_id
        ).all()

    def get_seasonings_detail(self, recipe_id: str) -> List[dict]:
        """获取菜谱调料详情（含调料名称）"""
        rows = self.db.query(RecipeSeasoning, Seasoning).join(
            Seasoning, Seasoning.id == RecipeSeasoning.seasoning_id
        ).filter(RecipeSeasoning.recipe_id == recipe_id).all()
        return [
            {
                "id": rs.id,
                "seasoning_id": rs.seasoning_id,
                "seasoning_name": s.canonical_name,
                "quantity": rs.quantity,
            }
            for rs, s in rows
        ]

    # ---- 用户相关查询（供详情/列表使用）----
    def is_favorited(self, household_id: str, recipe_id: str) -> bool:
        """是否已收藏"""
        return self.db.query(Favorite.id).filter(
            and_(Favorite.household_id == household_id, Favorite.recipe_id == recipe_id)
        ).first() is not None

    def cooked_count(self, household_id: str, recipe_id: str) -> int:
        """该家庭把此菜谱加入过几天菜单"""
        return self.db.query(func.count(MealPlan.id)).filter(
            and_(MealPlan.household_id == household_id, MealPlan.recipe_id == recipe_id)
        ).scalar() or 0

    def is_in_today_menu(self, household_id: str, recipe_id: str) -> bool:
        """今天是否在菜单中"""
        return self.db.query(MealPlan.id).filter(
            and_(
                MealPlan.household_id == household_id,
                MealPlan.recipe_id == recipe_id,
                MealPlan.target_date == date.today().isoformat(),
            )
        ).first() is not None

    def record_history(self, household_id: str, recipe_id: str) -> None:
        """记录浏览历史（upsert：每家庭每菜谱一条，重复浏览刷新时间）"""
        from datetime import datetime
        history = self.db.query(RecipeHistory).filter(
            and_(RecipeHistory.household_id == household_id, RecipeHistory.recipe_id == recipe_id)
        ).first()
        if history:
            history.viewed_at = datetime.utcnow()
            history.updated_at = datetime.utcnow()
        else:
            history = RecipeHistory(
                household_id=household_id,
                recipe_id=recipe_id,
                viewed_at=datetime.utcnow(),
            )
            self.db.add(history)
        self.db.commit()

    def publish_recipe(self, recipe_id: str) -> Optional[Recipe]:
        """发布菜谱"""
        recipe = self.get_by_id(recipe_id)
        if not recipe:
            return None

        from datetime import datetime
        recipe.status = "published"
        recipe.revision += 1
        recipe.updated_at = datetime.utcnow()
        self.db.commit()
        self.db.refresh(recipe)
        return recipe

    # ---- RAG 索引数据装配 ----

    def get_full_for_index(self, recipe_id: str) -> Optional[dict]:
        """装配全量菜谱数据供 RAG 切块（含来源 URL）。

        返回普通 dict（非 ORM/Pydantic），供 chunking 消费；
        不在 rag 层复用 RecipeService._to_response，避免循环依赖。
        """
        recipe = self.db.query(Recipe).filter(Recipe.id == recipe_id).first()
        if not recipe:
            return None

        ing_rows = self.db.query(RecipeIngredient, Ingredient.canonical_name).join(
            Ingredient, Ingredient.id == RecipeIngredient.ingredient_id
        ).filter(RecipeIngredient.recipe_id == recipe_id).order_by(
            RecipeIngredient.sort_order
        ).all()
        step_rows = self.db.query(RecipeStep).filter(
            RecipeStep.recipe_id == recipe_id
        ).order_by(RecipeStep.step_no).all()
        tags = [t.name for t in self.get_tags(recipe_id)]
        categories = [c.name for c in self.get_categories(recipe_id)]
        seasonings = [s["seasoning_name"] for s in self.get_seasonings_detail(recipe_id)]

        return {
            "recipe_id": recipe.id,
            "title": recipe.title,
            "summary": recipe.summary,
            "cover": recipe.cover,
            "servings": recipe.servings,
            "prep_minutes": recipe.prep_minutes,
            "cook_minutes": recipe.cook_minutes,
            "difficulty": recipe.difficulty,
            "status": recipe.status,
            "revision": recipe.revision,
            "deleted_at": recipe.deleted_at,
            "source_url": recipe.source.source_url if recipe.source else None,
            "tags": tags,
            "categories": categories,
            "seasonings": seasonings,
            "ingredients": [
                {
                    "canonical_name": name,
                    "quantity": ri.quantity,
                    "unit": ri.unit,
                    "raw_quantity": ri.raw_quantity,
                    "preparation": ri.preparation,
                }
                for ri, name in ing_rows
            ],
            "steps": [
                {"step_no": s.step_no, "instruction": s.instruction}
                for s in step_rows
            ],
        }

    def list_published_ids(self) -> List[str]:
        """所有 published 且未软删的菜谱 ID（全量重建用）。"""
        rows = self.db.query(Recipe.id).filter(
            Recipe.status == "published",
            Recipe.deleted_at.is_(None),
        ).all()
        return [r[0] for r in rows]
