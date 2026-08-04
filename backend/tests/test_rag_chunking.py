"""RAG 切块单元测试（纯函数，不依赖 DB/Chroma/Ollama）"""
from app.rag.chunking import chunk_recipe, needs_reindex


def _data(**overrides):
    base = {
        "recipe_id": "r1",
        "title": "番茄炒鸡蛋",
        "summary": "家常快手菜",
        "revision": 2,
        "status": "published",
        "deleted_at": None,
        "source_url": "http://example.com/recipe/1",
        "tags": ["家常菜", "快手"],
        "categories": ["热菜"],
        "prep_minutes": 5,
        "cook_minutes": 10,
        "difficulty": "简单",
        "servings": 2,
        "ingredients": [
            {"canonical_name": "番茄", "quantity": "2", "unit": "个"},
            {"canonical_name": "鸡蛋", "quantity": "3", "unit": "个"},
        ],
        "steps": [
            {"step_no": 1, "instruction": "番茄切块"},
            {"step_no": 2, "instruction": "鸡蛋打散"},
            {"step_no": 3, "instruction": "热油下蛋"},
            {"step_no": 4, "instruction": "下番茄翻炒"},
            {"step_no": 5, "instruction": "调味出锅"},
        ],
    }
    base.update(overrides)
    return base


def test_chunk_types_present():
    chunks = chunk_recipe(_data())
    types = {c.chunk_type for c in chunks}
    assert "overview" in types
    assert "ingredients" in types
    assert "steps" in types


def test_overview_contains_title_and_tags():
    chunks = chunk_recipe(_data())
    overview = next(c for c in chunks if c.chunk_type == "overview")
    assert "番茄炒鸡蛋" in overview.text
    assert "家常菜" in overview.text
    assert "5分钟/10分钟" in overview.text


def test_steps_grouped_by_4():
    steps = [{"step_no": i, "instruction": f"步骤{i}"} for i in range(1, 10)]
    chunks = chunk_recipe(_data(steps=steps))
    step_chunks = [c for c in chunks if c.chunk_type == "steps"]
    assert len(step_chunks) == 3  # 9 步 → 4/4/1
    assert "第1步" in step_chunks[0].text and "第4步" in step_chunks[0].text
    assert "第5步" in step_chunks[1].text and "第8步" in step_chunks[1].text
    assert "第9步" in step_chunks[2].text


def test_content_hash_deterministic():
    c1 = chunk_recipe(_data())
    c2 = chunk_recipe(_data())
    assert [c.content_hash for c in c1] == [c.content_hash for c in c2]


def test_no_tips_chunk_when_missing():
    chunks = chunk_recipe(_data())
    assert all(c.chunk_type != "tips" for c in chunks)


def test_tips_chunk_when_present():
    chunks = chunk_recipe(_data(tips="出锅前淋香油"))
    assert any(c.chunk_type == "tips" and "香油" in c.text for c in chunks)


def test_single_recipe_only():
    chunks = chunk_recipe(_data())
    assert {c.recipe_id for c in chunks} == {"r1"}


def test_needs_reindex():
    data = _data()
    stored = [(c.revision, c.content_hash) for c in chunk_recipe(data)]
    assert needs_reindex(data, stored) is False
    assert needs_reindex(data, []) is True
    assert needs_reindex(_data(revision=3), stored) is True
    assert needs_reindex(_data(summary="改过的简介"), stored) is True
