"""分类管理模块测试（recipe/ingredient/seasoning 三类）"""
import uuid
import pytest
from fastapi.testclient import TestClient


def make_category(client, name="家常菜", type_="recipe", expect=201):
    """创建分类并返回响应"""
    return client.post(f"/api/v1/categories?type={type_}", json={"name": name})


class TestCategoriesAPI:
    """分类 API 测试类"""

    def test_create_category(self, client: TestClient):
        """测试创建菜谱分类"""
        response = make_category(client, "川菜", "recipe")
        assert response.status_code == 201
        data = response.json()
        assert data["name"] == "川菜"
        assert data["id"]

    def test_create_ingredient_category(self, client: TestClient):
        """测试创建食材分类"""
        response = make_category(client, "海鲜", "ingredient")
        assert response.status_code == 201

    def test_create_duplicate_name(self, client: TestClient):
        """测试创建重复名称分类"""
        make_category(client, "家常菜", "recipe")
        response = make_category(client, "家常菜", "recipe")
        assert response.status_code == 409

    def test_same_name_different_type(self, client: TestClient):
        """同名不同分类类型互不影响"""
        make_category(client, "默认菜系", "recipe")
        response = make_category(client, "默认菜系", "ingredient")
        assert response.status_code == 201

    def test_list_categories(self, client: TestClient):
        """测试分类列表"""
        make_category(client, "川菜", "recipe")
        make_category(client, "粤菜", "recipe")
        make_category(client, "海鲜", "ingredient")

        response = client.get("/api/v1/categories?type=recipe")
        assert response.status_code == 200
        data = response.json()
        names = [c["name"] for c in data["data"]]
        assert "川菜" in names and "粤菜" in names
        assert "海鲜" not in names

    def test_invalid_type(self, client: TestClient):
        """测试非法类型"""
        response = make_category(client, "川菜", "invalid")
        assert response.status_code == 422

    def test_update_category(self, client: TestClient):
        """测试重命名分类"""
        cat = make_category(client, "川菜", "recipe").json()
        response = client.patch(
            f"/api/v1/categories/{cat['id']}?type=recipe",
            json={"name": "蜀菜"}
        )
        assert response.status_code == 200
        assert response.json()["name"] == "蜀菜"

    def test_delete_category(self, client: TestClient):
        """测试删除分类"""
        cat = make_category(client, "川菜", "recipe").json()
        response = client.delete(f"/api/v1/categories/{cat['id']}?type=recipe")
        assert response.status_code == 204

        # 验证列表已不含该分类
        response = client.get("/api/v1/categories?type=recipe")
        names = [c["name"] for c in response.json()["data"]]
        assert "川菜" not in names

    def test_delete_default_category_protected(self, client: TestClient):
        """测试默认分类不可删除"""
        # 手动创建 id=1 的默认分类（生产环境由种子数据保证）
        from app.db.models import RecipeCategory
        from app.db.database import get_session_local
        db = get_session_local()()
        try:
            if not db.query(RecipeCategory).filter(RecipeCategory.id == "1").first():
                db.add(RecipeCategory(id="1", name="默认"))
                db.commit()
        finally:
            db.close()

        response = client.delete("/api/v1/categories/1?type=recipe")
        assert response.status_code == 400
        assert "默认分类" in response.json()["detail"]

    def test_delete_in_use_category(self, client: TestClient):
        """测试删除被菜谱引用的分类被拒绝"""
        cat = make_category(client, "川菜", "recipe").json()

        # 创建一个菜谱并关联该分类
        from app.db.models import Recipe, RecipeCategoryLink
        from app.db.database import get_session_local
        db = get_session_local()()
        try:
            recipe = Recipe(id=str(uuid.uuid4()), title="测试菜谱", status="draft")
            db.add(recipe)
            db.flush()
            db.add(RecipeCategoryLink(
                id=str(uuid.uuid4()), recipe_id=recipe.id, category_id=cat["id"]
            ))
            db.commit()
        finally:
            db.close()

        response = client.delete(f"/api/v1/categories/{cat['id']}?type=recipe")
        assert response.status_code == 400
