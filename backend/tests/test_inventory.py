"""库存管理模块测试"""
import pytest
from datetime import datetime, timedelta
from fastapi.testclient import TestClient


class TestInventoryAPI:
    """库存 API 测试类"""

    def test_create_household(self, client: TestClient):
        """测试创建家庭"""
        response = client.post(
            "/api/v1/inventory/households",
            json={
                "name": "测试家庭",
                "description": "用于测试的家庭"
            }
        )
        assert response.status_code == 201
        data = response.json()
        assert data["name"] == "测试家庭"

    def test_get_household(self, client: TestClient):
        """测试获取家庭信息"""
        # 先创建家庭
        create_response = client.post(
            "/api/v1/inventory/households",
            json={"name": "测试家庭"}
        )
        household_id = create_response.json()["id"]

        # 获取家庭信息
        response = client.get(f"/api/v1/inventory/households/{household_id}")
        assert response.status_code == 200
        data = response.json()
        assert data["name"] == "测试家庭"

    def test_get_household_not_found(self, client: TestClient):
        """测试获取不存在的家庭"""
        response = client.get("/api/v1/inventory/households/nonexistent-id")
        assert response.status_code == 404

    def test_create_inventory_item(self, client: TestClient, sample_ingredient):
        """测试创建库存物品"""
        # 先创建家庭
        household_response = client.post(
            "/api/v1/inventory/households",
            json={"name": "测试家庭"}
        )
        household_id = household_response.json()["id"]

        # 创建库存物品
        response = client.post(
            "/api/v1/inventory/items",
            json={
                "household_id": household_id,
                "ingredient_id": sample_ingredient.id,
                "quantity": "500",
                "unit": "克",
                "expires_at": (datetime.now() + timedelta(days=7)).isoformat(),
                "note": "测试备注"
            }
        )
        assert response.status_code == 201
        data = response.json()
        assert data["household_id"] == household_id
        assert data["quantity"] == "500"

    def test_create_inventory_item_duplicate(self, client: TestClient, sample_ingredient):
        """测试创建重复的库存物品"""
        # 先创建家庭
        household_response = client.post(
            "/api/v1/inventory/households",
            json={"name": "测试家庭"}
        )
        household_id = household_response.json()["id"]

        # 创建第一个库存物品
        client.post(
            "/api/v1/inventory/items",
            json={
                "household_id": household_id,
                "ingredient_id": sample_ingredient.id,
                "quantity": "500",
                "unit": "克"
            }
        )

        # 尝试创建重复的库存物品
        response = client.post(
            "/api/v1/inventory/items",
            json={
                "household_id": household_id,
                "ingredient_id": sample_ingredient.id,
                "quantity": "300",
                "unit": "克"
            }
        )
        assert response.status_code == 400

    def test_get_inventory_item(self, client: TestClient, sample_ingredient):
        """测试获取库存物品详情"""
        # 先创建家庭和库存物品
        household_response = client.post(
            "/api/v1/inventory/households",
            json={"name": "测试家庭"}
        )
        household_id = household_response.json()["id"]

        item_response = client.post(
            "/api/v1/inventory/items",
            json={
                "household_id": household_id,
                "ingredient_id": sample_ingredient.id,
                "quantity": "500",
                "unit": "克"
            }
        )
        item_id = item_response.json()["id"]

        # 获取库存物品详情
        response = client.get(f"/api/v1/inventory/items/{item_id}")
        assert response.status_code == 200
        data = response.json()
        assert data["quantity"] == "500"

    def test_get_inventory_item_not_found(self, client: TestClient):
        """测试获取不存在的库存物品"""
        response = client.get("/api/v1/inventory/items/nonexistent-id")
        assert response.status_code == 404

    def test_list_inventory_items(self, client: TestClient, sample_ingredient):
        """测试获取库存物品列表"""
        # 先创建家庭和库存物品
        household_response = client.post(
            "/api/v1/inventory/households",
            json={"name": "测试家庭"}
        )
        household_id = household_response.json()["id"]

        client.post(
            "/api/v1/inventory/items",
            json={
                "household_id": household_id,
                "ingredient_id": sample_ingredient.id,
                "quantity": "500",
                "unit": "克"
            }
        )

        # 获取库存列表
        response = client.get("/api/v1/inventory/items", params={"household_id": household_id})
        assert response.status_code == 200
        data = response.json()
        assert "data" in data
        assert "total" in data
        assert len(data["data"]) > 0

    def test_update_inventory_item(self, client: TestClient, sample_ingredient):
        """测试更新库存物品"""
        # 先创建家庭和库存物品
        household_response = client.post(
            "/api/v1/inventory/households",
            json={"name": "测试家庭"}
        )
        household_id = household_response.json()["id"]

        item_response = client.post(
            "/api/v1/inventory/items",
            json={
                "household_id": household_id,
                "ingredient_id": sample_ingredient.id,
                "quantity": "500",
                "unit": "克"
            }
        )
        item_id = item_response.json()["id"]

        # 更新库存物品
        response = client.patch(
            f"/api/v1/inventory/items/{item_id}",
            json={"quantity": "300", "note": "已使用一部分"}
        )
        assert response.status_code == 200
        data = response.json()
        assert data["quantity"] == "300"
        assert data["note"] == "已使用一部分"

    def test_delete_inventory_item(self, client: TestClient, sample_ingredient):
        """测试删除库存物品"""
        # 先创建家庭和库存物品
        household_response = client.post(
            "/api/v1/inventory/households",
            json={"name": "测试家庭"}
        )
        household_id = household_response.json()["id"]

        item_response = client.post(
            "/api/v1/inventory/items",
            json={
                "household_id": household_id,
                "ingredient_id": sample_ingredient.id,
                "quantity": "500",
                "unit": "克"
            }
        )
        item_id = item_response.json()["id"]

        # 删除库存物品
        response = client.delete(f"/api/v1/inventory/items/{item_id}")
        assert response.status_code == 204

        # 验证已删除
        response = client.get(f"/api/v1/inventory/items/{item_id}")
        assert response.status_code == 404

    def test_get_expiring_soon(self, client: TestClient, sample_ingredient):
        """测试获取即将过期的物品"""
        # 先创建家庭
        household_response = client.post(
            "/api/v1/inventory/households",
            json={"name": "测试家庭"}
        )
        household_id = household_response.json()["id"]

        # 创建即将过期的库存物品
        client.post(
            "/api/v1/inventory/items",
            json={
                "household_id": household_id,
                "ingredient_id": sample_ingredient.id,
                "quantity": "500",
                "unit": "克",
                "expires_at": (datetime.now() + timedelta(days=3)).isoformat()
            }
        )

        # 获取即将过期的物品
        response = client.get(
            "/api/v1/inventory/expiring-soon",
            params={"household_id": household_id, "days": 7}
        )
        assert response.status_code == 200
        data = response.json()
        assert len(data) > 0
