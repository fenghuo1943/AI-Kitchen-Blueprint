from typing import List, Dict, Any


def build_recommendation_payload(ingredients: List[str], max_minutes: int | None = None) -> Dict[str, Any]:
    return {
        "results": [],
        "reasoning": [],
        "fallback_reason": "暂无满足条件的菜谱，建议放宽食材约束或补充库存。",
        "ingredients": ingredients,
        "max_minutes": max_minutes,
    }
