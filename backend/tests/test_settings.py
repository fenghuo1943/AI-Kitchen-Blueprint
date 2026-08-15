"""用户/家庭设置模块测试"""
import uuid
import pytest
from fastapi.testclient import TestClient


@pytest.fixture
def household(db_session):
    from app.db.models import Household
    h = Household(id=str(uuid.uuid4()), name="设置测试家庭")
    db_session.add(h)
    db_session.commit()
    return h


class TestSettingsAPI:
    """设置 API 测试类"""

    def test_defaults_when_nothing_set(self, client: TestClient, household):
        """未设置时返回默认值：电脑端 30、手机端 20"""
        res = client.get("/api/v1/settings", params={"household_id": household.id})
        assert res.status_code == 200
        assert res.json() == {"page_size_desktop": 30, "page_size_mobile": 20}

    def test_full_update_round_trip(self, client: TestClient, household):
        """PUT 两个值后 GET 能读回"""
        res = client.put(
            "/api/v1/settings",
            params={"household_id": household.id},
            json={"page_size_desktop": 40, "page_size_mobile": 25}
        )
        assert res.status_code == 200
        assert res.json() == {"page_size_desktop": 40, "page_size_mobile": 25}

        data = client.get("/api/v1/settings", params={"household_id": household.id}).json()
        assert data["page_size_desktop"] == 40
        assert data["page_size_mobile"] == 25

    def test_partial_update_keeps_other_key(self, client: TestClient, household):
        """只改一个 key 不影响另一个"""
        client.put(
            "/api/v1/settings",
            params={"household_id": household.id},
            json={"page_size_desktop": 50}
        )
        data = client.get("/api/v1/settings", params={"household_id": household.id}).json()
        assert data["page_size_desktop"] == 50
        assert data["page_size_mobile"] == 20  # 默认值保留

    def test_household_isolation(self, client: TestClient, db_session):
        """不同家庭的设置互不影响"""
        from app.db.models import Household
        h1 = Household(id=str(uuid.uuid4()), name="家庭A")
        h2 = Household(id=str(uuid.uuid4()), name="家庭B")
        db_session.add_all([h1, h2])
        db_session.commit()

        client.put(
            "/api/v1/settings",
            params={"household_id": h1.id},
            json={"page_size_desktop": 99}
        )
        data = client.get("/api/v1/settings", params={"household_id": h2.id}).json()
        assert data["page_size_desktop"] == 30  # 家庭B 仍为默认
        data = client.get("/api/v1/settings", params={"household_id": h1.id}).json()
        assert data["page_size_desktop"] == 99

    def test_out_of_range_rejected(self, client: TestClient, household):
        """越界值（>100）返回 422"""
        res = client.put(
            "/api/v1/settings",
            params={"household_id": household.id},
            json={"page_size_desktop": 500}
        )
        assert res.status_code == 422

    def test_default_household_resolution(self, client: TestClient):
        """不带 household_id → 落到默认家庭，PUT→GET 正常"""
        res = client.put(
            "/api/v1/settings",
            json={"page_size_desktop": 45, "page_size_mobile": 35}
        )
        assert res.status_code == 200
        assert res.json() == {"page_size_desktop": 45, "page_size_mobile": 35}

        data = client.get("/api/v1/settings").json()
        assert data["page_size_desktop"] == 45
        assert data["page_size_mobile"] == 35
