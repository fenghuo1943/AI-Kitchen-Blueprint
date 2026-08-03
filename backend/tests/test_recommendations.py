"""推荐引擎模块测试"""
import pytest
from fastapi.testclient import TestClient


class TestRecommendationsAPI:
    """推荐 API 测试类"""

    def test_get_recommendations_empty(self, client: TestClient):
        """测试空推荐请求"""
        response = client.post(
            "/api/v1/recommendations",
            json={
                "ingredients": [],
                "allow_missing": True
            }
        )
        assert response.status_code == 200
        data = response.json()
        assert "results" in data
        assert "total" in data
        assert "fallback_reason" in data

    def test_get_recommendations_with_ingredients(self, client: TestClient, sample_recipe):
        """测试带食材的推荐请求"""
        response = client.post(
            "/api/v1/recommendations",
            json={
                "ingredients": ["测试食材"],
                "allow_missing": True
            }
        )
        assert response.status_code == 200
        data = response.json()
        assert "results" in data

    def test_get_recommendations_with_time_limit(self, client: TestClient, sample_recipe):
        """测试带时间限制的推荐请求"""
        response = client.post(
            "/api/v1/recommendations",
            json={
                "ingredients": ["测试食材"],
                "max_minutes": 30,
                "allow_missing": True
            }
        )
        assert response.status_code == 200
        data = response.json()
        assert "results" in data

    def test_get_recommendations_with_goals(self, client: TestClient, sample_recipe):
        """测试带目标标签的推荐请求"""
        response = client.post(
            "/api/v1/recommendations",
            json={
                "ingredients": ["测试食材"],
                "goals": ["简单", "快速"],
                "allow_missing": True
            }
        )
        assert response.status_code == 200
        data = response.json()
        assert "results" in data

    def test_get_recommendations_no_allow_missing(self, client: TestClient, sample_recipe):
        """测试不允许缺料的推荐请求"""
        response = client.post(
            "/api/v1/recommendations",
            json={
                "ingredients": ["测试食材"],
                "allow_missing": False
            }
        )
        assert response.status_code == 200
        data = response.json()
        assert "results" in data

    def test_calculate_coverage(self, client: TestClient, sample_recipe, sample_ingredient):
        """测试计算食材覆盖率"""
        response = client.post(
            "/api/v1/recommendations/coverage",
            json={
                "recipe_id": sample_recipe.id,
                "available_ingredients": [sample_ingredient.canonical_name]
            }
        )
        assert response.status_code == 200
        data = response.json()
        assert "coverage_score" in data
        assert "matched_ingredients" in data
        assert "missing_ingredients" in data

    def test_calculate_coverage_not_found(self, client: TestClient):
        """测试计算不存在菜谱的覆盖率"""
        response = client.post(
            "/api/v1/recommendations/coverage",
            json={
                "recipe_id": "nonexistent-id",
                "available_ingredients": []
            }
        )
        assert response.status_code == 404


class TestRecommendationEngine:
    """推荐引擎领域逻辑测试"""

    def test_calculate_ingredient_coverage_full_match(self):
        """测试完全匹配的覆盖率计算"""
        from app.domain.recommendation import RecommendationEngine

        required = [("鸡蛋", False), ("番茄", False)]
        available = ["鸡蛋", "番茄"]

        coverage, matched, missing = RecommendationEngine.calculate_ingredient_coverage(
            required, available
        )

        assert coverage == 1.0
        assert len(matched) == 2
        assert len(missing) == 0

    def test_calculate_ingredient_coverage_partial_match(self):
        """测试部分匹配的覆盖率计算"""
        from app.domain.recommendation import RecommendationEngine

        # 测试缺少必需食材的情况
        required = [("鸡蛋", False), ("番茄", False), ("葱", False)]
        available = ["鸡蛋", "番茄"]

        coverage, matched, missing = RecommendationEngine.calculate_ingredient_coverage(
            required, available
        )

        assert coverage == 2 / 3
        assert len(matched) == 2
        assert "葱" in missing

    def test_calculate_ingredient_coverage_no_match(self):
        """测试无匹配的覆盖率计算"""
        from app.domain.recommendation import RecommendationEngine

        required = [("鸡蛋", False), ("番茄", False)]
        available = ["土豆", "白菜"]

        coverage, matched, missing = RecommendationEngine.calculate_ingredient_coverage(
            required, available
        )

        assert coverage == 0.0
        assert len(matched) == 0
        assert len(missing) == 2

    def test_calculate_time_score(self):
        """测试时间分数计算"""
        from app.domain.recommendation import RecommendationEngine

        # 完全在时间限制内
        score = RecommendationEngine.calculate_time_score(10, 20, 60)
        assert score > 0

        # 超出时间限制
        score = RecommendationEngine.calculate_time_score(30, 40, 60)
        assert score == 0.0

    def test_calculate_tag_score(self):
        """测试标签分数计算"""
        from app.domain.recommendation import RecommendationEngine

        # 完全匹配
        score = RecommendationEngine.calculate_tag_score(
            ["简单", "快速", "家常"],
            ["简单", "快速"]
        )
        assert score == 1.0

        # 部分匹配
        score = RecommendationEngine.calculate_tag_score(
            ["简单", "家常"],
            ["简单", "快速"]
        )
        assert score == 0.5

        # 无匹配
        score = RecommendationEngine.calculate_tag_score(
            ["家常"],
            ["简单", "快速"]
        )
        assert score == 0.0

    def test_should_include_recipe(self):
        """测试是否应该包含菜谱"""
        from app.domain.recommendation import RecommendationEngine

        # 允许缺料，有匹配
        assert RecommendationEngine.should_include_recipe(0.5, True, True) == True

        # 不允许缺料，有缺失
        assert RecommendationEngine.should_include_recipe(0.5, False, True) == False

        # 不允许缺料，无缺失
        assert RecommendationEngine.should_include_recipe(0.5, False, False) == True

        # 允许缺料，但无匹配
        assert RecommendationEngine.should_include_recipe(0.0, True, True) == False
