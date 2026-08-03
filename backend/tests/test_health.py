"""健康检查接口测试"""
from fastapi.testclient import TestClient


def test_health_check(client: TestClient):
    """测试健康检查接口"""
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert "version" in data
    assert "environment" in data


def test_health_check_response_format(client: TestClient):
    """测试健康检查响应格式"""
    response = client.get("/health")
    data = response.json()
    required_fields = ["status", "version", "environment"]
    for field in required_fields:
        assert field in data, f"缺少必填字段: {field}"
