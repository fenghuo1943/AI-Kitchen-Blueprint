"""推荐领域逻辑"""
from typing import List, Tuple, Optional, Set
from dataclasses import dataclass


@dataclass
class IngredientMatch:
    """食材匹配结果"""
    ingredient_name: str
    is_matched: bool
    is_optional: bool


@dataclass
class RecipeScore:
    """菜谱评分"""
    recipe_id: str
    coverage_score: float  # 食材覆盖率 (0-1)
    match_score: float     # 匹配分数 (0-1)
    time_score: float      # 时间分数 (0-1)
    tag_score: float       # 标签匹配分数 (0-1)
    overall_score: float   # 综合分数 (0-1)


@dataclass
class HardConstraintResult:
    """硬约束检查结果"""
    passed: bool
    failed_constraints: List[str]


class RecommendationEngine:
    """推荐引擎领域逻辑"""

    # 权重配置
    WEIGHTS = {
        "coverage": 0.4,      # 食材覆盖率权重
        "match": 0.2,         # 匹配分数权重
        "time": 0.2,          # 时间分数权重
        "tag": 0.2,           # 标签匹配权重
    }

    @staticmethod
    def check_hard_constraints(
        recipe_allergens: List[str],
        recipe_tags: List[str],
        recipe_prep_minutes: int,
        recipe_cook_minutes: int,
        recipe_season_months: Optional[List[str]],
        user_allergens_exclude: Optional[List[str]],
        user_equipment: Optional[List[str]],
        user_max_minutes: Optional[int],
        user_season_month: Optional[str]
    ) -> HardConstraintResult:
        """
        检查硬约束

        Args:
            recipe_allergens: 菜谱包含的过敏原
            recipe_tags: 菜谱标签（包含设备、季节等信息）
            recipe_prep_minutes: 准备时间
            recipe_cook_minutes: 烹饪时间
            recipe_season_months: 菜谱适合的季节月份
            user_allergens_exclude: 用户排除的过敏原
            user_equipment: 用户拥有的设备
            user_max_minutes: 用户最大允许时间
            user_season_month: 当前季节月份

        Returns:
            硬约束检查结果
        """
        failed = []

        # 1. 过敏原检查
        if user_allergens_exclude and recipe_allergens:
            user_allergens_set = {a.lower() for a in user_allergens_exclude}
            recipe_allergens_set = {a.lower() for a in recipe_allergens}
            conflicting = user_allergens_set.intersection(recipe_allergens_set)
            if conflicting:
                failed.append(f"包含过敏原: {', '.join(conflicting)}")

        # 2. 设备检查
        if user_equipment:
            # 检查菜谱是否需要特定设备（通过标签判断）
            equipment_tags = {"快炒", "炖煮", "烤箱", "微波炉", "空气炸锅", "蒸锅"}
            required_equipment = set(recipe_tags).intersection(equipment_tags)
            user_equipment_set = {e.lower() for e in user_equipment}

            for equipment in required_equipment:
                if equipment.lower() not in user_equipment_set:
                    failed.append(f"需要设备: {equipment}")

        # 3. 时间检查
        if user_max_minutes is not None:
            total_time = (recipe_prep_minutes or 0) + (recipe_cook_minutes or 0)
            if total_time > user_max_minutes:
                failed.append(f"烹饪时间 {total_time} 分钟超过限制 {user_max_minutes} 分钟")

        # 4. 季节检查
        if user_season_month and recipe_season_months:
            if user_season_month not in recipe_season_months:
                failed.append(f"不适合当前季节 (月份 {user_season_month})")

        return HardConstraintResult(
            passed=len(failed) == 0,
            failed_constraints=failed
        )

    @staticmethod
    def calculate_ingredient_coverage(
        required_ingredients: List[Tuple[str, bool]],  # (name, is_optional)
        available_ingredients: List[str]
    ) -> Tuple[float, List[str], List[str]]:
        """
        计算食材覆盖率

        Args:
            required_ingredients: 需要的食材列表，每个元素为 (食材名, 是否可选)
            available_ingredients: 现有的食材列表

        Returns:
            (覆盖率, 匹配的食材列表, 缺少的食材列表)
        """
        if not required_ingredients:
            return 1.0, [], []

        # 标准化食材名称
        available_set = {name.lower().strip() for name in available_ingredients}

        matched = []
        missing = []
        required_count = 0

        for ingredient_name, is_optional in required_ingredients:
            if not is_optional:
                required_count += 1

            if ingredient_name.lower().strip() in available_set:
                matched.append(ingredient_name)
            elif not is_optional:
                missing.append(ingredient_name)

        if required_count == 0:
            return 1.0, matched, missing

        coverage = len(matched) / len(required_ingredients) if required_ingredients else 0.0
        return coverage, matched, missing

    @staticmethod
    def calculate_time_score(
        prep_minutes: int,
        cook_minutes: int,
        max_minutes: int
    ) -> float:
        """
        计算时间分数

        Args:
            prep_minutes: 准备时间
            cook_minutes: 烹饪时间
            max_minutes: 最大允许时间

        Returns:
            时间分数 (0-1)，1表示时间最短
        """
        total_time = (prep_minutes or 0) + (cook_minutes or 0)

        if max_minutes <= 0:
            return 0.0

        if total_time <= 0:
            return 1.0

        if total_time > max_minutes:
            return 0.0

        # 时间越短分数越高
        return 1.0 - (total_time / max_minutes)

    @staticmethod
    def calculate_tag_score(
        recipe_tags: List[str],
        target_tags: List[str]
    ) -> float:
        """
        计算标签匹配分数

        Args:
            recipe_tags: 菜谱标签列表
            target_tags: 目标标签列表

        Returns:
            标签匹配分数 (0-1)
        """
        if not target_tags:
            return 1.0

        if not recipe_tags:
            return 0.0

        recipe_tags_lower = {tag.lower() for tag in recipe_tags}
        matched_count = sum(
            1 for tag in target_tags
            if tag.lower() in recipe_tags_lower
        )

        return matched_count / len(target_tags)

    @classmethod
    def calculate_overall_score(
        cls,
        coverage_score: float,
        match_score: float,
        time_score: float,
        tag_score: float
    ) -> float:
        """
        计算综合分数

        Args:
            coverage_score: 食材覆盖率
            match_score: 匹配分数
            time_score: 时间分数
            tag_score: 标签匹配分数

        Returns:
            综合分数 (0-1)
        """
        return (
            cls.WEIGHTS["coverage"] * coverage_score +
            cls.WEIGHTS["match"] * match_score +
            cls.WEIGHTS["time"] * time_score +
            cls.WEIGHTS["tag"] * tag_score
        )

    @classmethod
    def score_recipe(
        cls,
        recipe_tags: List[str],
        required_ingredients: List[Tuple[str, bool]],
        available_ingredients: List[str],
        prep_minutes: int,
        cook_minutes: int,
        max_minutes: int,
        target_tags: List[str]
    ) -> RecipeScore:
        """
        对菜谱进行评分

        Args:
            recipe_tags: 菜谱标签列表
            required_ingredients: 需要的食材列表
            available_ingredients: 现有的食材列表
            prep_minutes: 准备时间
            cook_minutes: 烹饪时间
            max_minutes: 最大允许时间
            target_tags: 目标标签列表

        Returns:
            菜谱评分结果
        """
        coverage_score, _, _ = cls.calculate_ingredient_coverage(
            required_ingredients, available_ingredients
        )

        # 匹配分数等于覆盖率
        match_score = coverage_score

        # 时间分数
        time_score = cls.calculate_time_score(prep_minutes, cook_minutes, max_minutes)

        # 标签分数
        tag_score = cls.calculate_tag_score(recipe_tags, target_tags)

        # 综合分数
        overall_score = cls.calculate_overall_score(
            coverage_score, match_score, time_score, tag_score
        )

        return RecipeScore(
            recipe_id="",
            coverage_score=coverage_score,
            match_score=match_score,
            time_score=time_score,
            tag_score=tag_score,
            overall_score=overall_score
        )

    @staticmethod
    def should_include_recipe(
        coverage_score: float,
        allow_missing: bool,
        has_missing_required: bool
    ) -> bool:
        """
        判断是否应该包含该菜谱

        Args:
            coverage_score: 食材覆盖率
            allow_missing: 是否允许缺料
            has_missing_required: 是否缺少必需食材

        Returns:
            是否应该包含
        """
        if not allow_missing and has_missing_required:
            return False

        # 如果允许缺料，至少需要匹配一些食材
        if allow_missing and coverage_score == 0:
            return False

        return True
