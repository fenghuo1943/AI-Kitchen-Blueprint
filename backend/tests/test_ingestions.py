"""入库任务模块测试"""
import pytest
from fastapi.testclient import TestClient


class TestIngestionsAPI:
    """入库任务 API 测试类"""

    def test_create_manual_ingestion(self, client: TestClient):
        """测试创建人工录入的入库任务"""
        response = client.post(
            "/api/v1/ingestions",
            json={
                "source_type": "manual",
                "import_mode": "draft",
                "recipe_data": {
                    "title": "测试入库菜谱",
                    "summary": "这是一个测试入库的菜谱",
                    "servings": 2,
                    "prep_minutes": 10,
                    "cook_minutes": 20,
                    "difficulty": "简单",
                    "ingredients": [
                        {"name": "鸡蛋", "quantity": "2", "unit": "个"},
                        {"name": "番茄", "quantity": "1", "unit": "个"}
                    ],
                    "steps": [
                        {"instruction": "第一步操作"},
                        {"instruction": "第二步操作"}
                    ],
                    "tags": ["家常菜", "简单"]
                }
            }
        )
        assert response.status_code == 201
        data = response.json()
        assert data["status"] == "succeeded"
        assert data["stage"] == "published"
        assert data["result_recipe_id"] is not None

    def test_manual_ingestion_auto_classifies(self, client: TestClient):
        """人工录入入库后：菜谱/食材按规则自动归类"""
        create = client.post(
            "/api/v1/ingestions",
            json={
                "source_type": "manual",
                "import_mode": "draft",
                "recipe_data": {
                    "title": "红烧肉",
                    "ingredients": [
                        {"name": "番茄", "quantity": "1", "unit": "个"},
                        {"name": "鸡蛋", "quantity": "2", "unit": "个"},
                    ],
                    "steps": [{"instruction": "先炒后炖"}],
                },
            }
        )
        assert create.status_code == 201
        recipe_id = create.json()["result_recipe_id"]
        assert recipe_id

        recipe = client.get(f"/api/v1/recipes/{recipe_id}").json()
        # 菜谱：红烧肉 → 炖菜
        assert "炖菜" in [c["name"] for c in recipe["categories"]]
        # 食材：番茄 → 蔬菜，鸡蛋 → 蛋类（自动归类并创建同名分类）
        ing_ids = {i["ingredient_name"]: i["ingredient_id"] for i in recipe["ingredients"]}
        tomato = client.get(f"/api/v1/ingredients/{ing_ids['番茄']}").json()
        egg = client.get(f"/api/v1/ingredients/{ing_ids['鸡蛋']}").json()
        assert tomato["category_name"] == "蔬菜"
        assert egg["category_name"] == "蛋类"

    def test_create_manual_ingestion_missing_data(self, client: TestClient):
        """测试创建人工录入的入库任务（缺少数据）"""
        response = client.post(
            "/api/v1/ingestions",
            json={
                "source_type": "manual",
                "import_mode": "draft"
            }
        )
        assert response.status_code == 400

    def test_create_url_ingestion(self, client: TestClient):
        """测试创建URL来源的入库任务"""
        response = client.post(
            "/api/v1/ingestions",
            json={
                "source_type": "url",
                "source_ref": "https://example.com/recipe/123",
                "import_mode": "draft"
            }
        )
        assert response.status_code == 201
        data = response.json()
        assert data["status"] == "queued"

    def test_create_duplicate_url_ingestion(self, client: TestClient):
        """测试创建重复URL的入库任务"""
        # 第一次创建
        client.post(
            "/api/v1/ingestions",
            json={
                "source_type": "url",
                "source_ref": "https://example.com/recipe/456",
                "import_mode": "draft"
            }
        )

        # 第二次创建相同URL
        response = client.post(
            "/api/v1/ingestions",
            json={
                "source_type": "url",
                "source_ref": "https://example.com/recipe/456",
                "import_mode": "draft"
            }
        )
        assert response.status_code == 400

    def test_get_ingestion(self, client: TestClient):
        """测试获取入库任务详情"""
        # 先创建任务
        create_response = client.post(
            "/api/v1/ingestions",
            json={
                "source_type": "manual",
                "import_mode": "draft",
                "recipe_data": {
                    "title": "测试菜谱",
                    "ingredients": [],
                    "steps": []
                }
            }
        )
        job_id = create_response.json()["id"]

        # 获取详情
        response = client.get(f"/api/v1/ingestions/{job_id}")
        assert response.status_code == 200
        data = response.json()
        assert data["id"] == job_id

    def test_get_ingestion_not_found(self, client: TestClient):
        """测试获取不存在的入库任务"""
        response = client.get("/api/v1/ingestions/nonexistent-id")
        assert response.status_code == 404

    def test_list_ingestions(self, client: TestClient):
        """测试获取入库任务列表"""
        # 先创建一个任务
        client.post(
            "/api/v1/ingestions",
            json={
                "source_type": "manual",
                "import_mode": "draft",
                "recipe_data": {
                    "title": "测试菜谱",
                    "ingredients": [],
                    "steps": []
                }
            }
        )

        # 获取列表
        response = client.get("/api/v1/ingestions")
        assert response.status_code == 200
        data = response.json()
        assert "data" in data
        assert "total" in data
        assert len(data["data"]) > 0

    def test_list_ingestions_with_status_filter(self, client: TestClient):
        """测试按状态筛选入库任务列表"""
        # 先创建一个任务
        client.post(
            "/api/v1/ingestions",
            json={
                "source_type": "manual",
                "import_mode": "draft",
                "recipe_data": {
                    "title": "测试菜谱",
                    "ingredients": [],
                    "steps": []
                }
            }
        )

        # 按状态筛选
        response = client.get("/api/v1/ingestions", params={"status": "succeeded"})
        assert response.status_code == 200
        data = response.json()
        assert all(j["status"] == "succeeded" for j in data["data"])
