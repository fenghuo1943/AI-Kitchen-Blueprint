"""推荐数据访问层"""
import json
from typing import Optional, List, Tuple
from sqlalchemy.orm import Session

from app.db.models import Recipe, RecipeIngredient, RecipeTag, Tag, Ingredient


class RecommendationRepository:
    """推荐仓储类"""

    def __init__(self, db: Session):
        self.db = db

    def get_candidate_recipes(
        self,
        max_minutes: Optional[int] = None,
        tags: Optional[List[str]] = None,
        limit: int = 100
    ) -> List[Recipe]:
        """
        获取候选菜谱

        Args:
            max_minutes: 最大烹饪时间
            tags: 标签筛选
            limit: 返回数量限制

        Returns:
            候选菜谱列表
        """
        stmt = self.db.query(Recipe).filter(
            Recipe.status == "published",
            Recipe.deleted_at.is_(None)
        )

        # 时间筛选
        if max_minutes is not None:
            stmt = stmt.filter(
                (Recipe.cook_minutes + Recipe.prep_minutes) <= max_minutes
            )

        # 标签筛选
        if tags:
            stmt = stmt.join(RecipeTag).join(Tag).filter(Tag.name.in_(tags))

        return stmt.limit(limit).all()

    def get_recipe_ingredients(self, recipe_id: str) -> List[Tuple[str, bool]]:
        """
        获取菜谱的食材列表

        Args:
            recipe_id: 菜谱ID

        Returns:
            食材列表，每个元素为 (食材名, 是否可选)
        """
        results = self.db.query(
            Ingredient.canonical_name,
            RecipeIngredient.optional
        ).join(
            RecipeIngredient, RecipeIngredient.ingredient_id == Ingredient.id
        ).filter(
            RecipeIngredient.recipe_id == recipe_id
        ).all()

        return [(name, bool(optional)) for name, optional in results]

    def get_recipe_tags(self, recipe_id: str) -> List[str]:
        """
        获取菜谱的标签列表

        Args:
            recipe_id: 菜谱ID

        Returns:
            标签名称列表
        """
        results = self.db.query(Tag.name).join(
            RecipeTag, RecipeTag.tag_id == Tag.id
        ).filter(
            RecipeTag.recipe_id == recipe_id
        ).all()

        return [name for name, in results]

    def get_ingredient_by_name(self, name: str) -> Optional[Ingredient]:
        """
        根据名称获取食材

        Args:
            name: 食材名称

        Returns:
            食材对象
        """
        return self.db.query(Ingredient).filter(
            Ingredient.canonical_name == name,
            Ingredient.deleted_at.is_(None)
        ).first()

    def resolve_ingredient_names(self, names: List[str]) -> List[str]:
        """
        解析食材名称，支持别名

        Args:
            names: 食材名称列表

        Returns:
            标准化后的食材名称列表
        """
        resolved = []
        for name in names:
            # 直接匹配标准名称
            ingredient = self.get_ingredient_by_name(name)
            if ingredient:
                resolved.append(ingredient.canonical_name)
                continue

            # 尝试通过别名匹配
            from app.db.models import IngredientAlias
            alias = self.db.query(IngredientAlias).filter(
                IngredientAlias.alias == name
            ).first()

            if alias:
                ingredient = self.get_ingredient_by_id(alias.ingredient_id)
                if ingredient:
                    resolved.append(ingredient.canonical_name)
                    continue

            # 未找到，保留原名
            resolved.append(name)

        return resolved

    def get_ingredient_by_id(self, ingredient_id: str) -> Optional[Ingredient]:
        """
        根据ID获取食材

        Args:
            ingredient_id: 食材ID

        Returns:
            食材对象
        """
        return self.db.query(Ingredient).filter(
            Ingredient.id == ingredient_id,
            Ingredient.deleted_at.is_(None)
        ).first()

    def log_recommendation(
        self,
        request_hash: str,
        filters_json: dict,
        candidate_ids: List[str],
        rank_version: str
    ) -> None:
        """
        记录推荐日志

        Args:
            request_hash: 请求哈希
            filters_json: 筛选条件
            candidate_ids: 候选菜谱ID列表
            rank_version: 排序版本
        """
        from app.db.models import RecommendationLog
        import uuid

        log = RecommendationLog(
            id=str(uuid.uuid4()),
            request_hash=request_hash,
            filters_json=json.dumps(filters_json),
            candidate_ids=json.dumps(candidate_ids),
            rank_version=rank_version
        )
        self.db.add(log)
        self.db.commit()
