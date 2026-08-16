"""调料管理模块测试"""
import uuid
import pytest
from fastapi.testclient import TestClient


class TestSeasoningsAPI:
    """调料 API 测试类"""

    def _create_category(self, client):
        """创建调料分类"""
        return client.post("/api/v1/categories?type=seasoning", json={"name": "基础调料"}).json()

    def test_create_seasoning(self, client: TestClient):
        """测试创建调料（自动生成拼音）"""
        response = client.post(
            "/api/v1/seasonings",
            json={"canonical_name": "生抽"}
        )
        assert response.status_code == 201
        data = response.json()
        assert data["canonical_name"] == "生抽"
        assert data["pinyin"] == "shengchou"

    def test_create_seasoning_auto_classify(self, client: TestClient):
        """无 category_id 时按名称自动归类（生抽 → 基础调味）"""
        response = client.post(
            "/api/v1/seasonings",
            json={"canonical_name": "生抽"}
        )
        assert response.status_code == 201
        data = response.json()
        assert data["category_name"] == "基础调味"

    def test_create_seasoning_unknown_falls_back_default(self, client: TestClient):
        """未识别名称回落默认分类"""
        client.post("/api/v1/categories?type=seasoning", json={"name": "默认"})
        response = client.post(
            "/api/v1/seasonings",
            json={"canonical_name": "神秘调味品X"}
        )
        assert response.status_code == 201
        data = response.json()
        assert data["category_name"] == "默认"

    def test_create_seasoning_with_category(self, client: TestClient):
        """测试创建带分类的调料"""
        cat = self._create_category(client)
        response = client.post(
            "/api/v1/seasonings",
            json={"canonical_name": "盐", "category_id": cat["id"]}
        )
        assert response.status_code == 201
        assert response.json()["category_name"] == "基础调料"

    def test_create_duplicate(self, client: TestClient):
        """测试创建重复调料"""
        client.post("/api/v1/seasonings", json={"canonical_name": "盐"})
        response = client.post("/api/v1/seasonings", json={"canonical_name": "盐"})
        assert response.status_code == 409

    def test_search_by_pinyin(self, client: TestClient):
        """测试拼音搜索"""
        client.post("/api/v1/seasonings", json={"canonical_name": "生抽"})
        client.post("/api/v1/seasonings", json={"canonical_name": "老抽"})

        response = client.get("/api/v1/seasonings", params={"query": "sheng"})
        assert response.status_code == 200
        data = response.json()
        names = [s["canonical_name"] for s in data["data"]]
        assert "生抽" in names
        assert "老抽" not in names

    def test_search_by_name(self, client: TestClient):
        """测试按名称搜索"""
        client.post("/api/v1/seasonings", json={"canonical_name": "料酒"})
        response = client.get("/api/v1/seasonings", params={"query": "料酒"})
        assert response.json()["total"] == 1

    def test_filter_by_category(self, client: TestClient):
        """测试按分类筛选"""
        cat = self._create_category(client)
        client.post("/api/v1/seasonings", json={"canonical_name": "盐", "category_id": cat["id"]})
        client.post("/api/v1/seasonings", json={"canonical_name": "酱油"})

        response = client.get("/api/v1/seasonings", params={"category_id": cat["id"]})
        data = response.json()
        assert data["total"] == 1
        assert data["data"][0]["canonical_name"] == "盐"

    def test_get_seasoning(self, client: TestClient):
        """测试获取调料详情"""
        created = client.post("/api/v1/seasonings", json={"canonical_name": "醋"}).json()
        response = client.get(f"/api/v1/seasonings/{created['id']}")
        assert response.status_code == 200
        assert response.json()["canonical_name"] == "醋"

    def test_update_seasoning(self, client: TestClient):
        """测试更新调料（重算拼音）"""
        created = client.post("/api/v1/seasonings", json={"canonical_name": "醋"}).json()
        response = client.patch(
            f"/api/v1/seasonings/{created['id']}",
            json={"canonical_name": "陈醋"}
        )
        assert response.status_code == 200
        data = response.json()
        assert data["canonical_name"] == "陈醋"
        assert data["pinyin"] == "chencu"

    def test_delete_seasoning(self, client: TestClient):
        """测试删除调料"""
        created = client.post("/api/v1/seasonings", json={"canonical_name": "味精"}).json()
        response = client.delete(f"/api/v1/seasonings/{created['id']}")
        assert response.status_code == 204

        # 验证已删除
        response = client.get(f"/api/v1/seasonings/{created['id']}")
        assert response.status_code == 404

    def test_delete_seasoning_in_use(self, client: TestClient, db_session):
        """测试删除被菜谱使用的调料被拒绝"""
        # 测试库用 StaticPool 单连接 + 外层事务，commit 不真正落库，
        # 需显式提交连接，避免首个 API 请求会话关闭时回滚清空数据。
        from app.db.models import Recipe, RecipeSeasoning, Seasoning
        import uuid

        seasoning = Seasoning(id=str(uuid.uuid4()), canonical_name="老抽")
        db_session.add(seasoning)
        recipe = Recipe(id=str(uuid.uuid4()), title="红烧肉", status="published")
        db_session.add(recipe)
        db_session.commit()

        link = RecipeSeasoning(
            id=str(uuid.uuid4()),
            recipe_id=recipe.id,
            seasoning_id=seasoning.id,
        )
        db_session.add(link)
        db_session.commit()
        db_session.connection().commit()

        response = client.delete(f"/api/v1/seasonings/{seasoning.id}")
        assert response.status_code == 409
        data = response.json()
        assert "红烧肉" in data["detail"]
        assert "1 个菜谱" in data["detail"]

        # 调料仍然存在
        resp = client.get(f"/api/v1/seasonings/{seasoning.id}")
        assert resp.status_code == 200

    def test_delete_seasoning_used_only_by_deleted_recipe(self, client: TestClient, db_session):
        """测试调料仅被软删除菜谱使用时，可正常删除"""
        from app.db.models import Recipe, RecipeSeasoning, Seasoning
        from datetime import datetime
        import uuid

        seasoning = Seasoning(id=str(uuid.uuid4()), canonical_name="蚝油")
        db_session.add(seasoning)
        recipe = Recipe(id=str(uuid.uuid4()), title="青菜", status="published", deleted_at=datetime.utcnow())
        db_session.add(recipe)
        db_session.commit()

        link = RecipeSeasoning(
            id=str(uuid.uuid4()),
            recipe_id=recipe.id,
            seasoning_id=seasoning.id,
        )
        db_session.add(link)
        db_session.commit()
        db_session.connection().commit()

        response = client.delete(f"/api/v1/seasonings/{seasoning.id}")
        assert response.status_code == 204


class TestSeasoningRecycleBinAPI:
    """调料回收站 API 测试类"""

    def _create_and_soft_delete(self, client, name="回收站调料"):
        """创建调料后软删除，返回 id"""
        created = client.post("/api/v1/seasonings", json={"canonical_name": name}).json()
        assert client.delete(f"/api/v1/seasonings/{created['id']}").status_code == 204
        return created["id"]

    def _deleted_ids(self, client):
        return [s["id"] for s in client.get("/api/v1/seasonings", params={"deleted": True}).json()["data"]]

    def test_list_deleted_seasonings(self, client):
        """测试列出回收站调料"""
        sea_id = self._create_and_soft_delete(client)
        assert sea_id in self._deleted_ids(client)

        # 未删除的不出现在回收站
        alive = client.post("/api/v1/seasonings", json={"canonical_name": "存活的调料"}).json()
        assert alive["id"] not in self._deleted_ids(client)

    def test_restore_seasoning(self, client):
        """测试恢复回收站调料"""
        sea_id = self._create_and_soft_delete(client)
        resp = client.post(f"/api/v1/seasonings/{sea_id}/restore")
        assert resp.status_code == 200
        assert resp.json()["deleted_at"] is None

        # 恢复后可正常查询，且不再出现在回收站
        assert client.get(f"/api/v1/seasonings/{sea_id}").status_code == 200
        assert sea_id not in self._deleted_ids(client)

    def test_restore_seasoning_not_found(self, client):
        """测试恢复不存在的调料"""
        assert client.post("/api/v1/seasonings/nonexistent-id/restore").status_code == 404

    def test_hard_delete_seasoning(self, client):
        """测试彻底删除回收站调料"""
        sea_id = self._create_and_soft_delete(client)
        resp = client.delete(f"/api/v1/seasonings/{sea_id}", params={"forever": True})
        assert resp.status_code == 204

        # 彻底删除后详情与回收站均不可见
        assert client.get(f"/api/v1/seasonings/{sea_id}").status_code == 404
        assert sea_id not in self._deleted_ids(client)

    def test_hard_delete_seasoning_in_use_by_deleted_recipe(self, client, db_session):
        """彻底删除仍被（软删）菜谱引用的调料被拒绝"""
        from app.db.models import Recipe, RecipeSeasoning, Seasoning
        from datetime import datetime
        import uuid

        seasoning = Seasoning(id=str(uuid.uuid4()), canonical_name="回收站蚝油")
        db_session.add(seasoning)
        recipe = Recipe(id=str(uuid.uuid4()), title="软删菜谱", status="published", deleted_at=datetime.utcnow())
        db_session.add(recipe)
        db_session.commit()

        link = RecipeSeasoning(
            id=str(uuid.uuid4()),
            recipe_id=recipe.id,
            seasoning_id=seasoning.id,
        )
        db_session.add(link)
        db_session.commit()
        db_session.connection().commit()

        # 仅被软删菜谱引用 → 可软删除入回收站
        resp = client.delete(f"/api/v1/seasonings/{seasoning.id}")
        assert resp.status_code == 204

        # 但彻底删除被拒绝
        resp = client.delete(f"/api/v1/seasonings/{seasoning.id}", params={"forever": True})
        assert resp.status_code == 409
        assert "引用" in resp.json()["detail"]
