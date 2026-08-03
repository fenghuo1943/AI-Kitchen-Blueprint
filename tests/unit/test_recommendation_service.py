from backend.app.services.recommendation_service import build_recommendation_payload


def test_build_recommendation_payload_returns_fallback():
    result = build_recommendation_payload(["鸡蛋", "番茄"])
    assert result["ingredients"] == ["鸡蛋", "番茄"]
    assert "fallback_reason" in result
