"""菜谱管理模块测试"""
import pytest
from fastapi.testclient import TestClient


class TestRecipesAPI:
    """菜谱 API 测试类"""

    def test_create_recipe(self, client: TestClient, sample_ingredient):
        """测试创建菜谱"""
        response = client.post(
            "/api/v1/recipes",
            json={
                "title": "测试菜谱",
                "summary": "这是一个测试菜谱",
                "servings": 2,
                "prep_minutes": 10,
                "cook_minutes": 20,
                "difficulty": "简单",
                "ingredients": [
                    {
                        "ingredient_id": sample_ingredient.id,
                        "quantity": "100",
                        "unit": "克",
                        "sort_order": 0
                    }
                ],
                "steps": [
                    {"step_no": 1, "instruction": "第一步操作"},
                    {"step_no": 2, "instruction": "第二步操作"}
                ],
                "tags": ["测试标签"]
            }
        )
        assert response.status_code == 201
        data = response.json()
        assert data["title"] == "测试菜谱"
        assert data["status"] == "draft"
        assert len(data["ingredients"]) == 1
        assert len(data["steps"]) == 2

    def test_get_recipe(self, client: TestClient, sample_recipe):
        """测试获取菜谱详情"""
        response = client.get(f"/api/v1/recipes/{sample_recipe.id}")
        assert response.status_code == 200
        data = response.json()
        assert data["title"] == sample_recipe.title

    def test_get_recipe_not_found(self, client: TestClient):
        """测试获取不存在的菜谱"""
        response = client.get("/api/v1/recipes/nonexistent-id")
        assert response.status_code == 404

    def test_list_recipes(self, client: TestClient, sample_recipe):
        """测试获取菜谱列表"""
        response = client.get("/api/v1/recipes")
        assert response.status_code == 200
        data = response.json()
        assert "data" in data
        assert "total" in data
        assert len(data["data"]) > 0

    def test_search_recipes(self, client: TestClient, sample_recipe):
        """测试搜索菜谱"""
        response = client.get("/api/v1/recipes", params={"query": "测试"})
        assert response.status_code == 200
        data = response.json()
        assert len(data["data"]) > 0

    def test_update_recipe(self, client: TestClient, sample_recipe):
        """测试更新菜谱"""
        response = client.patch(
            f"/api/v1/recipes/{sample_recipe.id}",
            json={"title": "更新后的标题", "summary": "更新后的摘要"}
        )
        assert response.status_code == 200
        data = response.json()
        assert data["title"] == "更新后的标题"
        assert data["summary"] == "更新后的摘要"

    def test_update_recipe_not_found(self, client: TestClient):
        """测试更新不存在的菜谱"""
        response = client.patch(
            "/api/v1/recipes/nonexistent-id",
            json={"title": "更新"}
        )
        assert response.status_code == 404

    def test_delete_recipe(self, client: TestClient, sample_recipe):
        """测试删除菜谱"""
        response = client.delete(f"/api/v1/recipes/{sample_recipe.id}")
        assert response.status_code == 204

        # 验证已删除
        response = client.get(f"/api/v1/recipes/{sample_recipe.id}")
        assert response.status_code == 404

    def test_publish_recipe(self, client: TestClient, sample_recipe):
        """测试发布菜谱"""
        response = client.post(f"/api/v1/recipes/{sample_recipe.id}/publish")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "published"
        assert data["revision"] == 2

    def test_publish_recipe_not_found(self, client: TestClient):
        """测试发布不存在的菜谱"""
        response = client.post("/api/v1/recipes/nonexistent-id/publish")
        assert response.status_code == 404
