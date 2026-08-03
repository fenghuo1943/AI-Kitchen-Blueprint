"""发现/推荐模块测试"""
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


class TestDiscoverAPI:
    """发现 API 测试类"""

    def test_new_recipes_ordered(self, client: TestClient, household):
        """测试最新菜谱按创建时间倒序"""
        r1 = _mk_recipe(client, "菜谱一")
        r2 = _mk_recipe(client, "菜谱二")
        response = client.get("/api/v1/discover", params={"type": "new", "limit": 10})
        data = response.json()["list"]
        assert data[0]["id"] == r2["id"]
        assert data[1]["id"] == r1["id"]

    def test_random_recipes(self, client: TestClient, household):
        """测试随机菜谱"""
        for i in range(5):
            _mk_recipe(client, f"随机菜谱{i}")
        response = client.get("/api/v1/discover", params={"type": "random", "limit": 3})
        assert len(response.json()["list"]) == 3

    def test_hot_recipes_by_favorite(self, client: TestClient, household):
        """测试热门按收藏加权"""
        from app.db.models import Favorite
        from app.db.database import get_session_local
        r1 = _mk_recipe(client, "收藏菜谱")
        _mk_recipe(client, "普通菜谱")
        db = get_session_local()()
        try:
            db.add(Favorite(id=str(uuid.uuid4()), household_id=household.id, recipe_id=r1["id"]))
            db.commit()
        finally:
            db.close()

        response = client.get("/api/v1/discover", params={"type": "hot", "household_id": household.id})
        data = response.json()["list"]
        assert data[0]["id"] == r1["id"]
        assert data[0]["is_favorited"] is True

    def test_today_recommend_stable_within_day(self, client: TestClient, household):
        """测试今日推荐当日稳定"""
        for i in range(8):
            _mk_recipe(client, f"菜谱{i}")
        response1 = client.get("/api/v1/discover", params={"type": "today", "household_id": household.id})
        response2 = client.get("/api/v1/discover", params={"type": "today", "household_id": household.id})
        ids1 = [r["id"] for r in response1.json()["list"]]
        ids2 = [r["id"] for r in response2.json()["list"]]
        # 前 limit-2 条确定性（按日固定种子），后 2 条随机探索
        assert ids1[:4] == ids2[:4]
        assert len(ids1) == 6

    def test_today_recommend_prefers_favorited(self, client: TestClient, household):
        """测试今日推荐偏好收藏的菜谱"""
        from app.db.models import Favorite
        from app.db.database import get_session_local
        fav_recipe = _mk_recipe(client, "收藏的菜")
        for i in range(6):
            _mk_recipe(client, f"普通菜{i}")
        db = get_session_local()()
        try:
            db.add(Favorite(id=str(uuid.uuid4()), household_id=household.id, recipe_id=fav_recipe["id"]))
            db.commit()
        finally:
            db.close()

        response = client.get("/api/v1/discover", params={"type": "today", "household_id": household.id})
        data = response.json()["list"]
        # 收藏加 3 分，基本会进入确定性的 top 部分
        assert data[0]["id"] == fav_recipe["id"]
