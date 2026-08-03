"""每日菜单模块测试"""
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


def _mk_recipe(client, title="番茄炒蛋", ingredient_ids=None, seasonings=None):
    payload = {"title": title}
    if ingredient_ids:
        payload["ingredients"] = [
            {"ingredient_id": iid, "quantity": "100", "unit": "克", "sort_order": i}
            for i, iid in enumerate(ingredient_ids)
        ]
    if seasonings:
        payload["seasonings"] = seasonings
    return client.post("/api/v1/recipes", json=payload).json()


class TestMenuAPI:
    """菜单 API 测试类"""

    def test_add_to_menu(self, client: TestClient, household):
        """测试添加菜谱到某天"""
        recipe = _mk_recipe(client)
        response = client.post(
            "/api/v1/menu",
            params={"household_id": household.id},
            json={"recipe_id": recipe["id"], "date": "2026-08-05"}
        )
        assert response.status_code == 201

    def test_add_duplicate_conflict(self, client: TestClient, household):
        """测试同天同菜谱去重"""
        recipe = _mk_recipe(client)
        for _ in range(2):
            response = client.post(
                "/api/v1/menu",
                params={"household_id": household.id},
                json={"recipe_id": recipe["id"], "date": "2026-08-05"}
            )
        # 第一次 201，第二次 409
        assert response.status_code == 409

    def test_add_nonexistent_recipe(self, client: TestClient, household):
        """测试添加不存在的菜谱"""
        response = client.post(
            "/api/v1/menu",
            params={"household_id": household.id},
            json={"recipe_id": "nonexistent", "date": "2026-08-05"}
        )
        assert response.status_code == 404

    def test_get_by_date(self, client: TestClient, household):
        """测试获取某天菜单"""
        a = client.post("/api/v1/ingredients", json={"canonical_name": "番茄"}).json()
        b = client.post("/api/v1/ingredients", json={"canonical_name": "鸡蛋"}).json()
        sea = client.post("/api/v1/seasonings", json={"canonical_name": "酱油"}).json()
        r1 = _mk_recipe(client, "番茄炒蛋", ingredient_ids=[a["id"]], seasonings=[{"seasoning_id": sea["id"]}])
        r2 = _mk_recipe(client, "蒸蛋", ingredient_ids=[b["id"]])

        client.post("/api/v1/menu", params={"household_id": household.id},
                    json={"recipe_id": r1["id"], "date": "2026-08-05"})
        client.post("/api/v1/menu", params={"household_id": household.id},
                    json={"recipe_id": r2["id"], "date": "2026-08-05"})

        response = client.get("/api/v1/menu", params={"household_id": household.id, "date": "2026-08-05"})
        data = response.json()
        assert len(data["list"]) == 2
        # 今日食材聚合去重
        ing_names = {i["name"] for i in data["ing_list"]}
        assert ing_names == {"番茄", "鸡蛋"}
        # 今日调料聚合
        sea_names = {s["name"] for s in data["sea_list"]}
        assert sea_names == {"酱油"}

    def test_get_month_dates(self, client: TestClient, household):
        """测试获取某月有菜单的日期"""
        recipe = _mk_recipe(client)
        client.post("/api/v1/menu", params={"household_id": household.id},
                    json={"recipe_id": recipe["id"], "date": "2026-08-05"})
        client.post("/api/v1/menu", params={"household_id": household.id},
                    json={"recipe_id": recipe["id"], "date": "2026-08-12"})

        response = client.get("/api/v1/menu", params={"household_id": household.id, "month": "2026-08"})
        dates = response.json()["dates"]
        assert "2026-08-05" in dates
        assert "2026-08-12" in dates

        response = client.get("/api/v1/menu", params={"household_id": household.id, "month": "2026-07"})
        assert response.json()["dates"] == []

    def test_waterfall_pagination(self, client: TestClient, household):
        """测试瀑布流按天分组分页"""
        recipe = _mk_recipe(client)
        for day in range(1, 4):
            client.post("/api/v1/menu", params={"household_id": household.id},
                        json={"recipe_id": recipe["id"], "date": f"2026-08-0{day}"})

        response = client.get("/api/v1/menu", params={
            "household_id": household.id, "mode": "waterfall", "page": 1, "page_size": 2
        })
        data = response.json()
        assert len(data["list"]) == 2  # 2 天
        assert data["total_page"] == 2
        assert data["list"][0]["recipes"][0]["title"] == "番茄炒蛋"

    def test_remove_from_menu(self, client: TestClient, household):
        """测试删除某天某菜谱"""
        recipe = _mk_recipe(client)
        client.post("/api/v1/menu", params={"household_id": household.id},
                    json={"recipe_id": recipe["id"], "date": "2026-08-05"})

        response = client.delete(f"/api/v1/menu/{recipe['id']}",
                                 params={"household_id": household.id, "date": "2026-08-05"})
        assert response.status_code == 204

        data = client.get("/api/v1/menu", params={"household_id": household.id, "date": "2026-08-05"}).json()
        assert len(data["list"]) == 0

    def test_menu_isolated_by_household(self, client: TestClient, household, db_session):
        """测试菜单按家庭隔离"""
        from app.db.models import Household
        h2 = Household(id=str(uuid.uuid4()), name="家庭2")
        db_session.add(h2)
        db_session.commit()

        recipe = _mk_recipe(client)
        client.post("/api/v1/menu", params={"household_id": household.id},
                    json={"recipe_id": recipe["id"], "date": "2026-08-05"})

        data = client.get("/api/v1/menu", params={"household_id": h2.id, "date": "2026-08-05"}).json()
        assert len(data["list"]) == 0
