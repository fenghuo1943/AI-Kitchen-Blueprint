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

    def test_list_recipes_sort_score_no_keyword(self, client: TestClient, sample_recipe):
        """回归测试：无关键词 + sort=score 不应报错（MySQL 中常量 literal 不能用于 ORDER BY）"""
        response = client.get("/api/v1/recipes", params={"sort": "score", "order": "desc"})
        assert response.status_code == 200
        data = response.json()
        assert "data" in data
        assert "total" in data

    def test_list_recipes_sort_score_no_keyword_asc(self, client: TestClient, sample_recipe):
        """回归测试：无关键词 + sort=score 升序同样不应报错"""
        response = client.get("/api/v1/recipes", params={"sort": "score", "order": "asc"})
        assert response.status_code == 200
        data = response.json()
        assert "data" in data

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

    def test_create_recipe_auto_classifies_category(self, client: TestClient):
        """无 category_ids 时按标题自动归类（红烧肉 → 炖菜）"""
        response = client.post(
            "/api/v1/recipes",
            json={
                "title": "红烧肉",
                "steps": [{"step_no": 1, "instruction": "小火慢炖"}],
            }
        )
        assert response.status_code == 201
        data = response.json()
        assert "炖菜" in [c["name"] for c in data["categories"]]

    def test_create_recipe_respects_explicit_categories(self, client: TestClient):
        """显式 category_ids 原样保留，不被自动分类覆盖"""
        cat = client.post("/api/v1/categories?type=recipe", json={"name": "川菜"}).json()
        response = client.post(
            "/api/v1/recipes",
            json={
                "title": "麻婆豆腐",
                "category_ids": [cat["id"]],
                "steps": [{"step_no": 1, "instruction": "麻辣炒制"}],
            }
        )
        assert response.status_code == 201
        data = response.json()
        assert [c["name"] for c in data["categories"]] == ["川菜"]

    def test_update_recipe_clear_categories_falls_back_default(self, client: TestClient, sample_recipe):
        """update 清空 category_ids 回落默认（用户显式清空，不自动重分类）"""
        client.post("/api/v1/categories?type=recipe", json={"name": "默认"})
        cat = client.post("/api/v1/categories?type=recipe", json={"name": "川菜"}).json()
        client.patch(f"/api/v1/recipes/{sample_recipe.id}", json={"category_ids": [cat["id"]]})
        response = client.patch(f"/api/v1/recipes/{sample_recipe.id}", json={"category_ids": []})
        assert response.status_code == 200
        assert [c["name"] for c in response.json()["categories"]] == ["默认"]

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


class TestRecipeRecycleBinAPI:
    """菜谱回收站 API 测试类"""

    def _create_and_soft_delete(self, client, title="回收站菜谱"):
        """创建菜谱后软删除，返回 id"""
        created = client.post("/api/v1/recipes", json={"title": title}).json()
        assert client.delete(f"/api/v1/recipes/{created['id']}").status_code == 204
        return created["id"]

    def _deleted_ids(self, client):
        return [r["id"] for r in client.get("/api/v1/recipes", params={"deleted": True}).json()["data"]]

    def test_batch_hard_delete_recipes(self, client):
        """测试批量彻底删除回收站菜谱"""
        id1 = self._create_and_soft_delete(client, "批量删菜谱A")
        id2 = self._create_and_soft_delete(client, "批量删菜谱B")

        resp = client.post("/api/v1/recipes/batch-delete", json={"ids": [id1, id2]})
        assert resp.status_code == 200
        data = resp.json()
        assert data["deleted_count"] == 2
        assert data["failed"] == []

        deleted_ids = self._deleted_ids(client)
        assert id1 not in deleted_ids
        assert id2 not in deleted_ids

    def test_batch_hard_delete_recipe_already_gone(self, client):
        """批量删除中已不存在的 id 视为已删除"""
        resp = client.post("/api/v1/recipes/batch-delete", json={"ids": ["nonexistent-id"]})
        assert resp.status_code == 200
        data = resp.json()
        assert data["deleted_count"] == 1
        assert data["failed"] == []

    def test_recycle_bin_contains_deleted_review_recipe(self, client):
        """回归测试：软删除的 review 状态菜谱应在回收站可见"""
        # 创建菜谱后改为 review 状态，再软删除
        created = client.post("/api/v1/recipes", json={"title": "待审菜谱"}).json()
        updated = client.patch(
            f"/api/v1/recipes/{created['id']}",
            json={"status": "review"},
        )
        assert updated.status_code == 200
        assert updated.json()["status"] == "review"
        assert client.delete(f"/api/v1/recipes/{created['id']}").status_code == 204

        # 回收站应包含该 review 菜谱
        assert created["id"] in self._deleted_ids(client)

        # 正常列表（非回收站）仍不应展示 review 菜谱
        normal_ids = [r["id"] for r in client.get("/api/v1/recipes").json()["data"]]
        assert created["id"] not in normal_ids
