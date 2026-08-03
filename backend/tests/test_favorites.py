"""收藏模块测试"""
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


class TestFavoritesAPI:
    """收藏 API 测试类"""

    def test_add_favorite(self, client: TestClient, household):
        """测试收藏"""
        recipe = _mk_recipe(client)
        response = client.post(
            "/api/v1/favorites",
            params={"household_id": household.id},
            json={"recipe_id": recipe["id"]}
        )
        assert response.status_code == 201
        assert response.json()["recipe_id"] == recipe["id"]

    def test_add_duplicate_idempotent(self, client: TestClient, household):
        """测试重复收藏幂等"""
        recipe = _mk_recipe(client)
        for _ in range(2):
            response = client.post(
                "/api/v1/favorites",
                params={"household_id": household.id},
                json={"recipe_id": recipe["id"]}
            )
            assert response.status_code == 201

        # 列表只有一条
        response = client.get("/api/v1/favorites", params={"household_id": household.id})
        assert response.json()["total"] == 1

    def test_add_nonexistent_recipe(self, client: TestClient, household):
        """测试收藏不存在的菜谱"""
        response = client.post(
            "/api/v1/favorites",
            params={"household_id": household.id},
            json={"recipe_id": "nonexistent"}
        )
        assert response.status_code == 404

    def test_list_favorites(self, client: TestClient, household):
        """测试收藏列表（含菜谱标题）"""
        recipe = _mk_recipe(client, "红烧肉")
        client.post("/api/v1/favorites", params={"household_id": household.id},
                    json={"recipe_id": recipe["id"]})

        response = client.get("/api/v1/favorites", params={"household_id": household.id})
        data = response.json()
        assert data["total"] == 1
        assert data["data"][0]["recipe_title"] == "红烧肉"

    def test_remove_favorite(self, client: TestClient, household):
        """测试取消收藏"""
        recipe = _mk_recipe(client)
        client.post("/api/v1/favorites", params={"household_id": household.id},
                    json={"recipe_id": recipe["id"]})

        response = client.delete(f"/api/v1/favorites/{recipe['id']}",
                                 params={"household_id": household.id})
        assert response.status_code == 204
        assert client.get("/api/v1/favorites", params={"household_id": household.id}).json()["total"] == 0

    def test_favorites_isolated_by_household(self, client: TestClient, household, db_session):
        """测试收藏按家庭隔离"""
        from app.db.models import Household
        h2 = Household(id=str(uuid.uuid4()), name="家庭2")
        db_session.add(h2)
        db_session.commit()

        recipe = _mk_recipe(client)
        client.post("/api/v1/favorites", params={"household_id": household.id},
                    json={"recipe_id": recipe["id"]})

        assert client.get("/api/v1/favorites", params={"household_id": household.id}).json()["total"] == 1
        assert client.get("/api/v1/favorites", params={"household_id": h2.id}).json()["total"] == 0

    def test_deleted_recipe_hidden_from_favorites(self, client: TestClient, household):
        """测试软删除菜谱不出现在收藏列表"""
        recipe = _mk_recipe(client)
        client.post("/api/v1/favorites", params={"household_id": household.id},
                    json={"recipe_id": recipe["id"]})
        client.delete(f"/api/v1/recipes/{recipe['id']}")

        response = client.get("/api/v1/favorites", params={"household_id": household.id})
        assert response.json()["total"] == 0
