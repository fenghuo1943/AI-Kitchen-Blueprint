"""菜谱搜索升级与 CRUD 增强测试（参考 cook 移植）"""
import uuid
import pytest
from fastapi.testclient import TestClient


@pytest.fixture
def household(db_session):
    """测试家庭"""
    from app.db.models import Household
    h = Household(id=str(uuid.uuid4()), name="测试家庭")
    db_session.add(h)
    db_session.commit()
    return h


@pytest.fixture
def category(db_session):
    """测试菜谱分类"""
    from app.db.models import RecipeCategory
    c = RecipeCategory(id=str(uuid.uuid4()), name="家常菜")
    db_session.add(c)
    db_session.commit()
    return c


def _mk_recipe(client, title, ingredient_ids=None, category_ids=None, seasonings=None):
    """通过 API 创建菜谱"""
    payload = {"title": title, "summary": f"{title}的简介", "difficulty": "简单"}
    if ingredient_ids:
        payload["ingredients"] = [
            {"ingredient_id": iid, "quantity": "100", "unit": "克", "sort_order": idx}
            for idx, iid in enumerate(ingredient_ids)
        ]
    if category_ids:
        payload["category_ids"] = category_ids
    if seasonings:
        payload["seasonings"] = seasonings
    return client.post("/api/v1/recipes", json=payload)


class TestRecipeSearch:
    """菜谱搜索升级测试"""

    def test_search_by_pinyin(self, client: TestClient, household):
        """测试拼音搜索：输入拼音前缀可搜到中文菜谱"""
        r = _mk_recipe(client, "番茄炒蛋")
        rid = r.json()["id"]
        response = client.get("/api/v1/recipes", params={"q": "fanqie"})
        assert response.status_code == 200
        assert response.json()["total"] == 1
        assert response.json()["data"][0]["id"] == rid

    def test_filter_by_ingredient_any(self, client: TestClient, household):
        """测试食材筛选（any：包含任一）"""
        a = client.post("/api/v1/ingredients", json={"canonical_name": "番茄"}).json()
        b = client.post("/api/v1/ingredients", json={"canonical_name": "鸡蛋"}).json()
        _mk_recipe(client, "番茄炒蛋", ingredient_ids=[a["id"]])
        _mk_recipe(client, "土豆烧肉")

        response = client.get("/api/v1/recipes", params={"ingredients": a["id"], "match": "any"})
        assert response.json()["total"] == 1
        assert response.json()["data"][0]["title"] == "番茄炒蛋"

    def test_filter_by_ingredient_exact(self, client: TestClient, household):
        """测试食材筛选（exact：必须同时包含全部）"""
        a = client.post("/api/v1/ingredients", json={"canonical_name": "番茄"}).json()
        b = client.post("/api/v1/ingredients", json={"canonical_name": "鸡蛋"}).json()
        c = client.post("/api/v1/ingredients", json={"canonical_name": "猪肉"}).json()
        _mk_recipe(client, "番茄炒蛋", ingredient_ids=[a["id"], b["id"]])
        _mk_recipe(client, "番茄炖肉", ingredient_ids=[a["id"], c["id"]])

        # 全含 a+b → 只有番茄炒蛋（番茄炖肉缺 b）
        response = client.get("/api/v1/recipes", params={"ingredients": f"{a['id']},{b['id']}", "match": "exact"})
        titles = [r["title"] for r in response.json()["data"]]
        assert titles == ["番茄炒蛋"]

        # 全含 a+c → 只有番茄炖肉
        response = client.get("/api/v1/recipes", params={"ingredients": f"{a['id']},{c['id']}", "match": "exact"})
        titles = [r["title"] for r in response.json()["data"]]
        assert titles == ["番茄炖肉"]

        # 只含 a（单食材全含=包含即可）→ 两道菜都含 a
        response = client.get("/api/v1/recipes", params={"ingredients": a["id"], "match": "exact"})
        assert response.json()["total"] == 2

    def test_filter_by_category(self, client: TestClient, household, category):
        """测试菜谱分类筛选"""
        _mk_recipe(client, "番茄炒蛋", category_ids=[category.id])
        _mk_recipe(client, "土豆烧肉")

        response = client.get("/api/v1/recipes", params={"category_id": category.id})
        titles = [r["title"] for r in response.json()["data"]]
        assert titles == ["番茄炒蛋"]

    def test_filter_ingredient_and_category_combo(self, client: TestClient, household, category):
        """测试食材+分类组合筛选"""
        a = client.post("/api/v1/ingredients", json={"canonical_name": "番茄"}).json()
        _mk_recipe(client, "番茄炒蛋", ingredient_ids=[a["id"]], category_ids=[category.id])
        _mk_recipe(client, "土豆烧肉", category_ids=[category.id])

        response = client.get("/api/v1/recipes", params={
            "ingredients": a["id"], "match": "any", "category_id": category.id
        })
        titles = [r["title"] for r in response.json()["data"]]
        assert titles == ["番茄炒蛋"]

    def test_search_keyword_matches_ingredient_name(self, client: TestClient, household):
        """测试关键词命中食材名"""
        a = client.post("/api/v1/ingredients", json={"canonical_name": "番茄"}).json()
        _mk_recipe(client, "红炒蛋", ingredient_ids=[a["id"]])

        response = client.get("/api/v1/recipes", params={"q": "番茄"})
        assert response.json()["total"] == 1
        assert response.json()["data"][0]["title"] == "红炒蛋"

    def test_sort_by_score(self, client: TestClient, household):
        """测试综合评分排序：标题命中(×6)优先于简介命中(×2)"""
        # 标题命中 + 简介不命中 → 6 分
        client.post("/api/v1/recipes", json={
            "title": "红烧肉", "summary": "经典的硬菜"
        })
        # 标题不命中 + 简介命中 → 2 分
        client.post("/api/v1/recipes", json={
            "title": "糖醋排骨", "summary": "红烧肉是经典做法"
        })

        response = client.get("/api/v1/recipes", params={"q": "红烧肉", "sort": "score"})
        titles = [r["title"] for r in response.json()["data"]]
        assert titles[0] == "红烧肉"
        assert titles[1] == "糖醋排骨"

    def test_list_response_has_new_fields(self, client: TestClient, household, category):
        """测试列表响应包含分类/收藏等新字段"""
        _mk_recipe(client, "番茄炒蛋", category_ids=[category.id])
        response = client.get("/api/v1/recipes", params={"household_id": household.id})
        item = response.json()["data"][0]
        assert "categories" in item
        assert "is_favorited" in item
        assert "is_in_today_menu" in item
        assert "cooked_count" in item
        assert "pinyin" in item

    def test_is_favorited_enrichment(self, client: TestClient, household):
        """测试收藏状态回填"""
        from app.db.models import Favorite, Recipe
        from app.db.database import get_session_local
        r = _mk_recipe(client, "番茄炒蛋").json()
        db = get_session_local()()
        try:
            db.add(Favorite(id=str(uuid.uuid4()), household_id=household.id, recipe_id=r["id"]))
            db.commit()
        finally:
            db.close()

        response = client.get("/api/v1/recipes", params={"household_id": household.id})
        item = response.json()["data"][0]
        assert item["is_favorited"] is True

    def test_total_score_boosted_by_favorite(self, client: TestClient, household):
        """测试收藏加权：收藏的菜谱综合分更高"""
        from app.db.models import Favorite
        from app.db.database import get_session_local
        r1 = _mk_recipe(client, "菜谱甲").json()
        r2 = _mk_recipe(client, "菜谱乙").json()
        db = get_session_local()()
        try:
            db.add(Favorite(id=str(uuid.uuid4()), household_id=household.id, recipe_id=r1["id"]))
            db.commit()
        finally:
            db.close()

        # 无关键词时仅按收藏权重排序
        response = client.get("/api/v1/recipes", params={"household_id": household.id, "sort": "score"})
        titles = [r["title"] for r in response.json()["data"]]
        assert titles[0] == "菜谱甲"


class TestRecipeRecycleBin:
    """回收站测试"""

    def test_soft_delete_moves_to_bin(self, client: TestClient, household):
        """测试软删除进回收站，正常列表不可见"""
        r = _mk_recipe(client, "番茄炒蛋").json()
        assert client.delete(f"/api/v1/recipes/{r['id']}").status_code == 204

        # 正常列表
        response = client.get("/api/v1/recipes")
        assert response.json()["total"] == 0

        # 回收站列表
        response = client.get("/api/v1/recipes", params={"deleted": "true"})
        assert response.json()["total"] == 1

    def test_restore(self, client: TestClient, household):
        """测试恢复"""
        r = _mk_recipe(client, "番茄炒蛋").json()
        client.delete(f"/api/v1/recipes/{r['id']}")
        assert client.post(f"/api/v1/recipes/{r['id']}/restore").status_code == 200

        response = client.get("/api/v1/recipes")
        assert response.json()["total"] == 1

    def test_hard_delete(self, client: TestClient, household):
        """测试彻底删除"""
        r = _mk_recipe(client, "番茄炒蛋").json()
        assert client.delete(f"/api/v1/recipes/{r['id']}", params={"forever": "true"}).status_code == 204

        # 正常与回收站都无
        assert client.get("/api/v1/recipes").json()["total"] == 0
        assert client.get("/api/v1/recipes", params={"deleted": "true"}).json()["total"] == 0

    def test_hard_delete_with_ingestion_candidates(self, client: TestClient, household, db_session):
        """彻底删除时存在 AI 采集候选外键引用（fk_candidate_recipe 无 ON DELETE CASCADE）不应报 1451"""
        from app.db.models import Recipe, IngestionJob, IngestionCandidate
        r = _mk_recipe(client, "西红柿牛腩").json()
        client.delete(f"/api/v1/recipes/{r['id']}")  # 软删除进回收站

        # 候选本体与补全目标都引用该菜谱
        job = IngestionJob(
            id=str(uuid.uuid4()),
            status="queued",
            stage="submitted",
            job_type="ai_search",
            request_text="西红柿",
            collection_mode="complete",
            target_recipe_id=r["id"],
            max_results=5,
        )
        db_session.add(job)
        db_session.add(IngestionCandidate(
            id=str(uuid.uuid4()),
            job_id=job.id,
            recipe_id=r["id"],
            target_recipe_id=r["id"],
        ))
        db_session.commit()

        # 触发 FK 约束的彻底删除
        assert client.delete(f"/api/v1/recipes/{r['id']}", params={"forever": "true"}).status_code == 204

        # 菜谱与候选已清除，任务补全目标置空而非残留外键
        assert db_session.query(Recipe).filter_by(id=r["id"]).count() == 0
        assert db_session.query(IngestionCandidate).filter_by(recipe_id=r["id"]).count() == 0
        db_session.refresh(job)
        assert job.target_recipe_id is None

    def test_recycle_bin_searchable(self, client: TestClient, household):
        """测试回收站内仍可搜索"""
        r = _mk_recipe(client, "被删除的菜谱").json()
        client.delete(f"/api/v1/recipes/{r['id']}")

        response = client.get("/api/v1/recipes", params={"deleted": "true", "q": "被删除"})
        assert response.json()["total"] == 1


class TestRecipeFullCRUD:
    """菜谱完整编辑测试"""

    def test_create_with_seasonings_and_categories(self, client: TestClient, household, category):
        """测试创建含调料和分类的菜谱"""
        sea = client.post("/api/v1/seasonings", json={"canonical_name": "酱油"}).json()
        r = _mk_recipe(client, "红烧肉", category_ids=[category.id],
                       seasonings=[{"seasoning_id": sea["id"], "quantity": "2勺"}]).json()

        response = client.get(f"/api/v1/recipes/{r['id']}")
        data = response.json()
        assert len(data["categories"]) == 1
        assert data["categories"][0]["name"] == "家常菜"
        assert len(data["seasonings"]) == 1
        assert data["seasonings"][0]["seasoning_name"] == "酱油"
        assert data["seasonings"][0]["quantity"] == "2勺"

    def test_full_update_rebuilds_relations(self, client: TestClient, household):
        """测试完整更新：食材/步骤/调料/分类删了重建"""
        a = client.post("/api/v1/ingredients", json={"canonical_name": "番茄"}).json()
        b = client.post("/api/v1/ingredients", json={"canonical_name": "猪肉"}).json()
        sea = client.post("/api/v1/seasonings", json={"canonical_name": "酱油"}).json()
        cat1 = client.post("/api/v1/categories?type=recipe", json={"name": "川菜"}).json()
        cat2 = client.post("/api/v1/categories?type=recipe", json={"name": "粤菜"}).json()

        # 初始：用番茄 + 分类1 + 无调料
        r = _mk_recipe(client, "炒菜", ingredient_ids=[a["id"]], category_ids=[cat1["id"]]).json()

        # 更新：换成猪肉 + 步骤 + 调料 + 分类2
        response = client.patch(f"/api/v1/recipes/{r['id']}", json={
            "title": "肉末茄子",
            "ingredients": [{"ingredient_id": b["id"], "quantity": "200", "unit": "克", "sort_order": 0}],
            "steps": [{"step_no": 1, "instruction": "猪肉切末"}, {"step_no": 2, "instruction": "翻炒"}],
            "category_ids": [cat2["id"]],
            "seasonings": [{"seasoning_id": sea["id"], "quantity": "1勺"}],
            "tags": ["家常"],
        })
        assert response.status_code == 200

        data = response.json()
        assert data["title"] == "肉末茄子"
        assert data["pinyin"] == "roumoqiezi"
        assert len(data["ingredients"]) == 1
        assert data["ingredients"][0]["ingredient_name"] == "猪肉"
        assert len(data["steps"]) == 2
        assert len(data["categories"]) == 1
        assert data["categories"][0]["name"] == "粤菜"
        assert len(data["seasonings"]) == 1
        assert len(data["tags"]) == 1

    def test_get_recipe_records_history(self, client: TestClient, household):
        """测试打开详情记录浏览历史"""
        from app.db.models import RecipeHistory
        from app.db.database import get_session_local
        r = _mk_recipe(client, "番茄炒蛋").json()
        client.get(f"/api/v1/recipes/{r['id']}", params={"household_id": household.id})

        db = get_session_local()()
        try:
            history = db.query(RecipeHistory).filter(
                RecipeHistory.household_id == household.id,
                RecipeHistory.recipe_id == r["id"],
            ).first()
            assert history is not None
        finally:
            db.close()
