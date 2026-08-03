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
