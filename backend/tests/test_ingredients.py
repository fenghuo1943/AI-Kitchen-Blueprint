"""食材管理模块测试"""
import pytest
from fastapi.testclient import TestClient


class TestIngredientsAPI:
    """食材 API 测试类"""

    def test_create_ingredient(self, client: TestClient):
        """测试创建食材"""
        response = client.post(
            "/api/v1/ingredients",
            json={
                "canonical_name": "白菜",
                "category": "蔬菜",
                "season_months": ["10", "11", "12", "1", "2", "3"],
                "allergens": [],
                "aliases": ["大白菜", "黄芽菜"]
            }
        )
        assert response.status_code == 201
        data = response.json()
        assert data["canonical_name"] == "白菜"
        assert data["category"] == "蔬菜"
        assert len(data["aliases"]) == 2

    def test_create_ingredient_duplicate_name(self, client: TestClient, sample_ingredient):
        """测试创建重复名称的食材"""
        response = client.post(
            "/api/v1/ingredients",
            json={
                "canonical_name": sample_ingredient.canonical_name,
                "category": "蔬菜"
            }
        )
        assert response.status_code == 409

    def test_get_ingredient(self, client: TestClient, sample_ingredient):
        """测试获取食材详情"""
        response = client.get(f"/api/v1/ingredients/{sample_ingredient.id}")
        assert response.status_code == 200
        data = response.json()
        assert data["canonical_name"] == sample_ingredient.canonical_name

    def test_get_ingredient_not_found(self, client: TestClient):
        """测试获取不存在的食材"""
        response = client.get("/api/v1/ingredients/nonexistent-id")
        assert response.status_code == 404

    def test_list_ingredients(self, client: TestClient, sample_ingredient):
        """测试获取食材列表"""
        response = client.get("/api/v1/ingredients")
        assert response.status_code == 200
        data = response.json()
        assert "data" in data
        assert "total" in data
        assert len(data["data"]) > 0

    def test_search_ingredients(self, client: TestClient, sample_ingredient):
        """测试搜索食材"""
        response = client.get("/api/v1/ingredients", params={"query": "测试"})
        assert response.status_code == 200
        data = response.json()
        assert len(data["data"]) > 0

    def test_update_ingredient(self, client: TestClient, sample_ingredient):
        """测试更新食材"""
        response = client.patch(
            f"/api/v1/ingredients/{sample_ingredient.id}",
            json={"category": "豆制品"}
        )
        assert response.status_code == 200
        data = response.json()
        assert data["category"] == "豆制品"

    def test_update_ingredient_not_found(self, client: TestClient):
        """测试更新不存在的食材"""
        response = client.patch(
            "/api/v1/ingredients/nonexistent-id",
            json={"category": "豆制品"}
        )
        assert response.status_code == 404

    def test_delete_ingredient(self, client: TestClient, sample_ingredient):
        """测试删除食材"""
        response = client.delete(f"/api/v1/ingredients/{sample_ingredient.id}")
        assert response.status_code == 204

        # 验证已删除
        response = client.get(f"/api/v1/ingredients/{sample_ingredient.id}")
        assert response.status_code == 404

    def test_add_alias(self, client: TestClient, sample_ingredient):
        """测试添加别名"""
        response = client.post(
            f"/api/v1/ingredients/{sample_ingredient.id}/aliases",
            params={"alias_name": "新别名"}
        )
        assert response.status_code == 201
        data = response.json()
        assert data["alias"] == "新别名"

    def test_add_alias_duplicate(self, client: TestClient, sample_ingredient):
        """测试添加重复别名"""
        # 先添加一个别名
        client.post(
            f"/api/v1/ingredients/{sample_ingredient.id}/aliases",
            params={"alias_name": "重复别名"}
        )

        # 再次添加相同别名
        response = client.post(
            f"/api/v1/ingredients/{sample_ingredient.id}/aliases",
            params={"alias_name": "重复别名"}
        )
        assert response.status_code == 409

    def test_create_ingredient_generates_pinyin(self, client: TestClient):
        """测试创建食材自动生成拼音"""
        response = client.post(
            "/api/v1/ingredients",
            json={"canonical_name": "胡萝卜"}
        )
        assert response.status_code == 201
        assert response.json()["pinyin"] == "huluobo"

    def test_search_ingredient_by_pinyin(self, client: TestClient):
        """测试按拼音前缀搜索食材"""
        client.post("/api/v1/ingredients", json={"canonical_name": "胡萝卜"})
        response = client.get("/api/v1/ingredients", params={"query": "hulu"})
        assert response.status_code == 200
        assert response.json()["total"] == 1

    def test_create_ingredient_with_category_id(self, client: TestClient):
        """测试创建带分类ID的食材"""
        cat = client.post("/api/v1/categories?type=ingredient", json={"name": "蔬菜"}).json()
        response = client.post(
            "/api/v1/ingredients",
            json={"canonical_name": "菠菜", "category_id": cat["id"]}
        )
        assert response.status_code == 201
        data = response.json()
        assert data["category_id"] == cat["id"]
        assert data["category_name"] == "蔬菜"

    def test_filter_ingredient_by_category_id(self, client: TestClient):
        """测试按分类ID筛选食材"""
        cat = client.post("/api/v1/categories?type=ingredient", json={"name": "蔬菜"}).json()
        client.post("/api/v1/ingredients", json={"canonical_name": "菠菜", "category_id": cat["id"]})
        client.post("/api/v1/ingredients", json={"canonical_name": "鸡蛋"})

        response = client.get("/api/v1/ingredients", params={"category_id": cat["id"]})
        data = response.json()
        assert data["total"] == 1
        assert data["data"][0]["canonical_name"] == "菠菜"
