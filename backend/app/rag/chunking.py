"""RAG 切块：将菜谱装配 dict 切为稳定文本块，并生成 content_hash。

稳定文本用于嵌入与检索；content_hash 用于幂等判定（revision 或内容变化才重建）。
"""
import hashlib
from dataclasses import dataclass
from typing import List, Optional, Tuple

# 切块类型（与 document_chunks.chunk_type 的 CHECK 约束一致）
CHUNK_TYPES = ("overview", "ingredients", "steps", "tips")
# 步骤每 3~5 步一组
STEPS_PER_CHUNK = 4
# 单个 ingredients 块最多包含的食材行数
_INGREDIENTS_PER_CHUNK = 20


@dataclass
class Chunk:
    """单个切块"""
    recipe_id: str
    revision: int
    chunk_type: str
    text: str
    content_hash: str
    source_url: Optional[str]
    order: int  # 同类型内序号，用于 Chroma doc id


def _sha256(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _make_chunk(data: dict, chunk_type: str, text: str, order: int) -> Optional[Chunk]:
    """构造 Chunk；文本为空返回 None。"""
    text = text.strip()
    if not text:
        return None
    return Chunk(
        recipe_id=data["recipe_id"],
        revision=data["revision"],
        chunk_type=chunk_type,
        text=text,
        content_hash=_sha256(text),
        source_url=data.get("source_url"),
        order=order,
    )


def _overview_chunk(data: dict) -> Optional[Chunk]:
    """概览块：标题/简介/标签/分类/时长/难度/份量，仅拼非空字段（固定顺序）。"""
    parts = [f"标题：{data['title']}"]
    if data.get("summary"):
        parts.append(f"简介：{data['summary']}")
    tags = data.get("tags") or []
    if tags:
        parts.append("标签：" + "、".join(tags))
    categories = data.get("categories") or []
    if categories:
        parts.append("分类：" + "、".join(categories))
    if data.get("prep_minutes") is not None or data.get("cook_minutes") is not None:
        prep = data.get("prep_minutes") or 0
        cook = data.get("cook_minutes") or 0
        parts.append(f"准备/烹饪：{prep}分钟/{cook}分钟")
    if data.get("difficulty"):
        parts.append(f"难度：{data['difficulty']}")
    if data.get("servings") is not None:
        parts.append(f"份量：{data['servings']}人份")
    return _make_chunk(data, "overview", "\n".join(parts), order=0)


def _ingredients_chunks(data: dict) -> List[Chunk]:
    """食材块：每行「规范名（数量 单位，原始用量，处理）」，按 sort_order。"""
    ingredients = data.get("ingredients") or []
    if not ingredients:
        return []
    lines = []
    for ing in ingredients:
        name = ing.get("canonical_name") or "未知食材"
        qty_parts = []
        if ing.get("quantity"):
            qty_parts.append(str(ing["quantity"]))
        if ing.get("unit"):
            qty_parts.append(str(ing["unit"]))
        detail = name
        if qty_parts:
            detail += "（" + " ".join(qty_parts)
            if ing.get("raw_quantity"):
                detail += f"，原始：{ing['raw_quantity']}"
            if ing.get("preparation"):
                detail += f"，{ing['preparation']}"
            detail += "）"
        lines.append(detail)

    chunks = []
    for i in range(0, len(lines), _INGREDIENTS_PER_CHUNK):
        text = "食材：\n" + "\n".join(lines[i:i + _INGREDIENTS_PER_CHUNK])
        chunk = _make_chunk(data, "ingredients", text, order=i // _INGREDIENTS_PER_CHUNK)
        if chunk:
            chunks.append(chunk)
    return chunks


def _steps_chunks(data: dict) -> List[Chunk]:
    """步骤块：每 STEPS_PER_CHUNK 步连续切一段。"""
    steps = sorted((data.get("steps") or []), key=lambda s: s.get("step_no", 0))
    if not steps:
        return []
    chunks = []
    for i in range(0, len(steps), STEPS_PER_CHUNK):
        group = steps[i:i + STEPS_PER_CHUNK]
        lines = [f"第{s['step_no']}步：{s['instruction']}" for s in group]
        text = "做法：\n" + "\n".join(lines)
        chunk = _make_chunk(data, "steps", text, order=i // STEPS_PER_CHUNK)
        if chunk:
            chunks.append(chunk)
    return chunks


def _tips_chunk(data: dict) -> List[Chunk]:
    """小贴士块（可选）：Recipe 模型暂无 tips 字段，data 含 tips 且非空才产出。"""
    tips = (data.get("tips") or "").strip()
    if not tips:
        return []
    chunk = _make_chunk(data, "tips", f"小贴士：{tips}", order=0)
    return [chunk] if chunk else []


def chunk_recipe(data: dict) -> List[Chunk]:
    """将一份菜谱装配的 dict 切分为 RAG 稳定文本块。

    data 来自 RecipeRepository.get_full_for_index。
    不同菜谱永不混入同一块；每个块只携带单道菜的 recipe_id。
    """
    chunks: List[Chunk] = []
    for candidate in (
        _overview_chunk(data),
        *_ingredients_chunks(data),
        *_steps_chunks(data),
        *_tips_chunk(data),
    ):
        if candidate is not None:
            chunks.append(candidate)
    return chunks


def needs_reindex(data: dict, stored: List[Tuple[int, str]]) -> bool:
    """判断是否需要重建索引。

    stored = [(revision, content_hash), ...] 来自 document_chunks 表。
    覆盖：首次发布、重发布（revision+1）、PATCH 改内容但 revision 未变。
    """
    if not stored:
        return True
    revisions = {r for r, _ in stored}
    if revisions != {data["revision"]}:
        return True
    new_hashes = {c.content_hash for c in chunk_recipe(data)}
    old_hashes = {h for _, h in stored}
    return new_hashes != old_hashes
