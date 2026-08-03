"""推荐业务逻辑层"""
import hashlib
import json
from typing import Optional, List
from datetime import datetime

from app.db.models import Recipe, Ingredient
from app.repositories.recommendation_repository import RecommendationRepository
from app.domain.recommendation import RecommendationEngine, RecipeScore
from app.schemas.recommendation import (
    RecommendationRequest, RecommendationResponse, RecommendationResult,
    IngredientCoverageRequest, IngredientCoverageResponse
)


class RecommendationService:
    """推荐服务类"""

    def __init__(self, repository: RecommendationRepository):
        self.repository = repository
        self.engine = RecommendationEngine()

    def get_recommendations(self, request: RecommendationRequest) -> RecommendationResponse:
        """
        获取推荐结果

        Args:
            request: 推荐请求

        Returns:
            推荐响应
        """
        # 解析食材名称（支持别名）
        available_ingredients = self.repository.resolve_ingredient_names(request.ingredients)

        # 获取候选菜谱
        candidate_recipes = self.repository.get_candidate_recipes(
            max_minutes=request.max_minutes,
            tags=request.goals,
            limit=100
        )

        # 对每个菜谱进行评分
        scored_recipes: List[tuple[Recipe, RecipeScore, List[str], List[str]]] = []

        for recipe in candidate_recipes:
            # 获取菜谱食材
            recipe_ingredients = self.repository.get_recipe_ingredients(recipe.id)

            # 获取菜谱标签
            recipe_tags = self.repository.get_recipe_tags(recipe.id)

            # 获取菜谱的过敏原信息
            recipe_allergens = self._get_recipe_allergens(recipe.id)

            # 获取菜谱的季节信息
            recipe_season_months = self._get_recipe_season_months(recipe.id)

            # 计算准备时间和烹饪时间
            prep_minutes = recipe.prep_minutes or 0
            cook_minutes = recipe.cook_minutes or 0

            # 检查硬约束
            constraint_result = self.engine.check_hard_constraints(
                recipe_allergens=recipe_allergens,
                recipe_tags=recipe_tags,
                recipe_prep_minutes=prep_minutes,
                recipe_cook_minutes=cook_minutes,
                recipe_season_months=recipe_season_months,
                user_allergens_exclude=request.diet_restrictions,
                user_equipment=request.equipment,
                user_max_minutes=request.max_minutes,
                user_season_month=request.season_month
            )

            # 如果硬约束检查失败，跳过该菜谱
            if not constraint_result.passed:
                continue

            # 计算覆盖率
            coverage_score, matched, missing = self.engine.calculate_ingredient_coverage(
                recipe_ingredients, available_ingredients
            )

            # 检查是否缺少必需食材
            has_missing_required = any(
                not is_optional and name in missing
                for name, is_optional in recipe_ingredients
            )

            # 判断是否应该包含
            if not self.engine.should_include_recipe(
                coverage_score, request.allow_missing, has_missing_required
            ):
                continue

            # 计算各维度分数
            time_score = self.engine.calculate_time_score(
                prep_minutes,
                cook_minutes,
                request.max_minutes or 9999
            )

            tag_score = self.engine.calculate_tag_score(
                recipe_tags, request.goals or []
            )

            # 综合分数
            overall_score = self.engine.calculate_overall_score(
                coverage_score, coverage_score, time_score, tag_score
            )

            score = RecipeScore(
                recipe_id=recipe.id,
                coverage_score=coverage_score,
                match_score=coverage_score,
                time_score=time_score,
                tag_score=tag_score,
                overall_score=overall_score
            )

            scored_recipes.append((recipe, score, matched, missing))

        # 按综合分数排序
        scored_recipes.sort(key=lambda x: x[1].overall_score, reverse=True)

        # 构建响应
        results = []
        for recipe, score, matched, missing in scored_recipes[:20]:  # 最多返回20个
            total_minutes = (recipe.prep_minutes or 0) + (recipe.cook_minutes or 0)

            # 生成推荐理由
            reason = self._generate_reason(score, matched, missing)

            results.append(RecommendationResult(
                recipe_id=recipe.id,
                recipe_title=recipe.title,
                recipe_summary=recipe.summary,
                servings=recipe.servings,
                total_minutes=total_minutes,
                difficulty=recipe.difficulty,
                matched_ingredients=matched,
                missing_ingredients=missing,
                coverage_score=score.coverage_score,
                overall_score=score.overall_score,
                reason=reason
            ))

        # 构建筛选条件
        filters_applied = {
            "ingredients": request.ingredients,
            "season_month": request.season_month,
            "max_minutes": request.max_minutes,
            "people_count": request.people_count,
            "equipment": request.equipment,
            "diet_restrictions": request.diet_restrictions,
            "goals": request.goals,
            "allow_missing": request.allow_missing
        }

        # 记录推荐日志
        request_hash = hashlib.md5(json.dumps(filters_applied, sort_keys=True).encode()).hexdigest()
        candidate_ids = [r.id for r in candidate_recipes]
        self.repository.log_recommendation(
            request_hash=request_hash,
            filters_json=filters_applied,
            candidate_ids=candidate_ids,
            rank_version="v1"
        )

        # 降级原因
        fallback_reason = None
        if not results:
            fallback_reason = "没有找到符合您条件的菜谱。您可以尝试放宽筛选条件，比如增加烹饪时间或允许缺料。"

        return RecommendationResponse(
            results=results,
            total=len(results),
            filters_applied=filters_applied,
            fallback_reason=fallback_reason
        )

    def calculate_coverage(self, request: IngredientCoverageRequest) -> IngredientCoverageResponse:
        """
        计算菜谱的食材覆盖率

        Args:
            request: 覆盖率计算请求

        Returns:
            覆盖率计算响应
        """
        # 获取菜谱信息
        recipe = self.repository.db.query(Recipe).filter(Recipe.id == request.recipe_id).first()
        if not recipe:
            raise ValueError("菜谱不存在")

        # 获取菜谱食材
        recipe_ingredients = self.repository.get_recipe_ingredients(request.recipe_id)

        # 解析食材名称
        available_ingredients = self.repository.resolve_ingredient_names(request.available_ingredients)

        # 计算覆盖率
        coverage_score, matched, missing = self.engine.calculate_ingredient_coverage(
            recipe_ingredients, available_ingredients
        )

        required_ingredients = [name for name, is_optional in recipe_ingredients if not is_optional]

        return IngredientCoverageResponse(
            recipe_id=recipe.id,
            recipe_title=recipe.title,
            coverage_score=coverage_score,
            matched_ingredients=matched,
            missing_ingredients=missing,
            required_ingredients=required_ingredients
        )

    def _get_recipe_allergens(self, recipe_id: str) -> List[str]:
        """获取菜谱的过敏原列表"""
        from app.db.models import RecipeIngredient, Ingredient

        ingredients = self.repository.db.query(Ingredient.allergens).join(
            RecipeIngredient, RecipeIngredient.ingredient_id == Ingredient.id
        ).filter(
            RecipeIngredient.recipe_id == recipe_id,
            Ingredient.allergens.isnot(None)
        ).all()

        allergens = set()
        for (allergens_json,) in ingredients:
            if allergens_json:
                try:
                    allergens.update(json.loads(allergens_json))
                except json.JSONDecodeError:
                    pass

        return list(allergens)

    def _get_recipe_season_months(self, recipe_id: str) -> Optional[List[str]]:
        """获取菜谱的季节月份"""
        from app.db.models import RecipeIngredient, Ingredient

        ingredients = self.repository.db.query(Ingredient.season_months).join(
            RecipeIngredient, RecipeIngredient.ingredient_id == Ingredient.id
        ).filter(
            RecipeIngredient.recipe_id == recipe_id,
            Ingredient.season_months.isnot(None)
        ).all()

        all_months = set()
        for (season_json,) in ingredients:
            if season_json:
                try:
                    all_months.update(json.loads(season_json))
                except json.JSONDecodeError:
                    pass

        return list(all_months) if all_months else None

    def _generate_reason(
        self,
        score: RecipeScore,
        matched: List[str],
        missing: List[str]
    ) -> str:
        """
        生成推荐理由

        Args:
            score: 评分结果
            matched: 匹配的食材
            missing: 缺少的食材

        Returns:
            推荐理由文本
        """
        parts = []

        # 食材匹配情况
        if matched:
            parts.append(f"您的食材「{'、'.join(matched[:3])}」都可以使用")
        if missing:
            parts.append(f"但还需要「{'、'.join(missing[:2])}」")

        # 时间情况
        if score.time_score > 0.7:
            parts.append("制作时间适中")
        elif score.time_score > 0.4:
            parts.append("制作需要一些时间")
        else:
            parts.append("制作时间较长")

        # 覆盖率
        coverage_percent = int(score.coverage_score * 100)
        parts.append(f"食材匹配度{coverage_percent}%")

        return "。".join(parts) + "。"
