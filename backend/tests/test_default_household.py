"""默认家庭测试：不传 household_id 时各功能自动落到默认家庭（应用层隐藏家庭概念）。"""
import uuid
from datetime import datetime, timedelta

import pytest
from fastapi.testclient import TestClient


def _mk_recipe(client, title="默认家庭测试菜谱"):
    return client.post("/api/v1/recipes", json={"title": title}).json()


class TestDefaultHousehold:
    """不传 household_id 时自动使用默认家庭"""

    def test_menu_no_household_creates_default(self, client: TestClient):
        """菜单接口不带 household_id → 201，自动创建一条「默认家庭」，数据可读回"""
        recipe = _mk_recipe(client)
        response = client.post(
            "/api/v1/menu",
            json={"recipe_id": recipe["id"], "date": "2026-08-05"}
        )
        assert response.status_code == 201

        # 自动创建了一条默认家庭
        households = client.get("/api/v1/inventory/households").json()
        assert households["total"] == 1
        assert households["data"][0]["name"] == "默认家庭"

        # 不带 household_id 也能读回
        data = client.get("/api/v1/menu", params={"date": "2026-08-05"}).json()
        assert len(data["list"]) == 1
        assert data["list"][0]["title"] == "默认家庭测试菜谱"

    def test_favorites_no_household_id(self, client: TestClient):
        """收藏接口不带 household_id → 201 且能读回"""
        recipe = _mk_recipe(client)
        response = client.post(
            "/api/v1/favorites",
            json={"recipe_id": recipe["id"]}
        )
        assert response.status_code == 201

        data = client.get("/api/v1/favorites").json()
        assert data["total"] == 1
        assert data["data"][0]["recipe_id"] == recipe["id"]

    def test_history_no_household_id(self, client: TestClient):
        """历史接口不带 household_id → 201 且能读回"""
        recipe = _mk_recipe(client)
        response = client.post(
            "/api/v1/history",
            json={"recipe_id": recipe["id"]}
        )
        assert response.status_code == 201

        data = client.get("/api/v1/history").json()
        assert data["total"] == 1

    def test_inventory_create_item_defaults_household(self, client: TestClient, sample_ingredient):
        """库存创建不带 household_id → 201，落到默认家庭且能读回"""
        response = client.post(
            "/api/v1/inventory/items",
            json={"ingredient_id": sample_ingredient.id, "quantity": "100", "unit": "克"}
        )
        assert response.status_code == 201
        created = response.json()

        default_id = client.get("/api/v1/inventory/households").json()["data"][0]["id"]
        assert created["household_id"] == default_id

        items = client.get("/api/v1/inventory/items").json()
        assert items["total"] == 1
        assert items["data"][0]["id"] == created["id"]

    def test_recipe_detail_records_history_to_default(self, client: TestClient, db_session):
        """打开菜谱详情（不带 household_id）→ 浏览历史落到默认家庭"""
        recipe = _mk_recipe(client)

        response = client.get(f"/api/v1/recipes/{recipe['id']}")
        assert response.status_code == 200

        from app.db.models import RecipeHistory
        rows = db_session.query(RecipeHistory).all()
        assert len(rows) == 1
        default_id = client.get("/api/v1/inventory/households").json()["data"][0]["id"]
        assert rows[0].household_id == default_id

    def test_resolver_uses_earliest_household(self, client: TestClient, db_session):
        """默认家庭 = created_at 最早的家庭（合并到最早家庭的规则）"""
        from app.db.models import Household
        older = Household(
            id=str(uuid.uuid4()), name="最早家庭",
            created_at=datetime.utcnow() - timedelta(days=1),
            updated_at=datetime.utcnow() - timedelta(days=1),
        )
        newer = Household(
            id=str(uuid.uuid4()), name="较晚家庭",
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow(),
        )
        db_session.add_all([older, newer])
        db_session.commit()

        recipe = _mk_recipe(client)
        response = client.post("/api/v1/favorites", json={"recipe_id": recipe["id"]})
        assert response.status_code == 201

        from app.db.models import Favorite
        fav = db_session.query(Favorite).one()
        assert fav.household_id == older.id

    def test_no_duplicate_default_creation(self, client: TestClient):
        """多次不带 household_id 的请求不会重复创建默认家庭"""
        recipe = _mk_recipe(client)
        client.post("/api/v1/favorites", json={"recipe_id": recipe["id"]})
        client.post("/api/v1/menu", json={"recipe_id": recipe["id"], "date": "2026-08-05"})

        households = client.get("/api/v1/inventory/households").json()
        assert households["total"] == 1
