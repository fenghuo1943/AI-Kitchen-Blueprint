"""浏览历史模块测试"""
import uuid
import pytest
from fastapi.testclient import TestClient


@pytest.fixture
def household(db_session):
    from app.db.models import Household
    h = Household(id=str(uuid.uuid4()), name="测试家庭")
    db_session.add(h)
    db_session.commit()
    return h


def _mk_recipe(client, title="番茄炒蛋"):
    return client.post("/api/v1/recipes", json={"title": title}).json()


class TestHistoryAPI:
    """浏览历史 API 测试类"""

    def test_record_history(self, client: TestClient, household):
        """测试手动记录历史"""
        recipe = _mk_recipe(client)
        response = client.post(
            "/api/v1/history",
            params={"household_id": household.id},
            json={"recipe_id": recipe["id"]}
        )
        assert response.status_code == 201
        assert response.json()["recipe_title"] == "番茄炒蛋"

    def test_record_upsert_dedupe(self, client: TestClient, household):
        """测试重复浏览去重置顶：同一菜谱只保留一条"""
        recipe = _mk_recipe(client)
        recipe2 = _mk_recipe(client, "土豆烧肉")

        for _ in range(3):
            client.post("/api/v1/history", params={"household_id": household.id},
                        json={"recipe_id": recipe["id"]})
        client.post("/api/v1/history", params={"household_id": household.id},
                    json={"recipe_id": recipe2["id"]})

        data = client.get("/api/v1/history", params={"household_id": household.id}).json()
        assert data["total"] == 2

    def test_history_recent_first(self, client: TestClient, household):
        """测试最近浏览置顶"""
        recipe1 = _mk_recipe(client, "菜谱一")
        recipe2 = _mk_recipe(client, "菜谱二")
        client.post("/api/v1/history", params={"household_id": household.id},
                    json={"recipe_id": recipe1["id"]})
        client.post("/api/v1/history", params={"household_id": household.id},
                    json={"recipe_id": recipe2["id"]})

        # 重复浏览 recipe1 → 置顶
        client.post("/api/v1/history", params={"household_id": household.id},
                    json={"recipe_id": recipe1["id"]})

        data = client.get("/api/v1/history", params={"household_id": household.id}).json()
        assert data["data"][0]["recipe_title"] == "菜谱一"

    def test_delete_one(self, client: TestClient, household):
        """测试删除单条历史"""
        recipe1 = _mk_recipe(client, "菜谱一")
        recipe2 = _mk_recipe(client, "菜谱二")
        for r in (recipe1, recipe2):
            client.post("/api/v1/history", params={"household_id": household.id},
                        json={"recipe_id": r["id"]})

        response = client.delete(f"/api/v1/history/{recipe1['id']}",
                                 params={"household_id": household.id})
        assert response.status_code == 204

        data = client.get("/api/v1/history", params={"household_id": household.id}).json()
        assert data["total"] == 1
        assert data["data"][0]["recipe_title"] == "菜谱二"

    def test_clear_history(self, client: TestClient, household):
        """测试清空历史"""
        recipe = _mk_recipe(client)
        client.post("/api/v1/history", params={"household_id": household.id},
                    json={"recipe_id": recipe["id"]})

        response = client.delete("/api/v1/history", params={"household_id": household.id})
        assert response.status_code == 204
        assert client.get("/api/v1/history", params={"household_id": household.id}).json()["total"] == 0

    def test_history_isolated_by_household(self, client: TestClient, household, db_session):
        """测试历史按家庭隔离"""
        from app.db.models import Household
        h2 = Household(id=str(uuid.uuid4()), name="家庭2")
        db_session.add(h2)
        db_session.commit()

        recipe = _mk_recipe(client)
        client.post("/api/v1/history", params={"household_id": household.id},
                    json={"recipe_id": recipe["id"]})

        assert client.get("/api/v1/history", params={"household_id": household.id}).json()["total"] == 1
        assert client.get("/api/v1/history", params={"household_id": h2.id}).json()["total"] == 0
