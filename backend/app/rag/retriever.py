"""语义检索：结构化硬约束过滤 → 向量召回 → 混合重排。

返回的 RetrievalHit.chunks 携带选中块原文（text/chunk_type/vector_score），
可直接作为后续 LLM 问答（C 阶段）的证据输入，检索器无需改动。
"""
import re
import time
from collections import defaultdict
from dataclasses import dataclass, field
from typing import Dict, List, Optional

from pypinyin import lazy_pinyin

from app.core.config import settings
from app.db.models import Ingredient, RecipeIngredient
from app.rag.embedding import EmbeddingUnavailableError, OllamaEmbeddingClient
from app.rag.vector_store import ChromaStore
from app.repositories.recipe_repository import RecipeRepository

# 混合重排权重：向量相似度 / 关键词重叠 / 食材命中
W_VEC = 0.5
W_KW = 0.3
W_ING = 0.2

# 结构化硬约束候选集上限
_MAX_CANDIDATES = 500


@dataclass
class RetrievalHit:
    recipe_id: str
    title: str
    cover: Optional[str]
    summary: Optional[str]
    score: float
    matched_ingredients: List[str] = field(default_factory=list)
    reasons: List[str] = field(default_factory=list)
    chunks: List[dict] = field(default_factory=list)  # [{chunk_type, text, vector_score}]


@dataclass
class RetrievalResult:
    hits: List[RetrievalHit]
    total: int
    engine_available: bool
    took_ms: int
    error: Optional[str] = None


def _keyword_tokens(text: str) -> set:
    """关键词分词：空白/标点切分 + 中文字符二元组 + 整句拼音。"""
    text = text.strip().lower()
    if not text:
        return set()
    terms = set(t for t in re.split(r"[\s,，。.!！?？、；;:：/]+", text) if t)
    bigrams = {text[i:i + 2] for i in range(len(text) - 1)}
    pinyin = "".join(lazy_pinyin(text))
    tokens = terms | bigrams | {pinyin}
    tokens.discard("")
    return tokens


def _keyword_overlap(tokens: set, title: str, summary: str) -> float:
    """关键词重叠分 0~1：标题命中权重高，简介次之。"""
    if not tokens:
        return 0.0
    title_l = (title or "").lower()
    summary_l = (summary or "").lower()
    title_hits = sum(1 for t in tokens if t in title_l)
    summary_hits = sum(1 for t in tokens if t in summary_l)
    if title_hits or summary_hits:
        return min(1.0, (title_hits * 2 + summary_hits) / len(tokens))
    return 0.0


def _ingredient_match(tokens: set, ingredient_names: List[str]) -> float:
    """食材命中分 0~1：查询 token 命中几种食材名，命中 3 种以上视为满分。"""
    if not tokens or not ingredient_names:
        return 0.0
    matched = {name for name in ingredient_names if any(t in name for t in tokens)}
    return min(1.0, len(matched) / 3)


def _load_ingredient_names(db, recipe_ids: List[str]) -> Dict[str, List[str]]:
    """批量加载菜谱的食材规范名（避免逐条懒加载 N+1）。"""
    if not recipe_ids:
        return {}
    rows = db.query(RecipeIngredient.recipe_id, Ingredient.canonical_name).join(
        Ingredient, Ingredient.id == RecipeIngredient.ingredient_id
    ).filter(RecipeIngredient.recipe_id.in_(recipe_ids)).all()
    mapping: Dict[str, List[str]] = defaultdict(list)
    for rid, name in rows:
        mapping[rid].append(name)
    return mapping


def _ms(start: float) -> int:
    return int((time.time() - start) * 1000)


class HybridRetriever:
    """检索器。"""

    def __init__(self, store: Optional[ChromaStore] = None,
                 embedding: Optional[OllamaEmbeddingClient] = None):
        self.store = store or ChromaStore()
        self.embedding = embedding or OllamaEmbeddingClient()

    def retrieve(self, db, query: str, filters: Optional[Dict] = None,
                 recall_top_k: int = settings.RECALL_TOP_K,
                 rerank_top_k: int = settings.RERANK_TOP_K) -> RetrievalResult:
        """执行检索。引擎（Ollama/Chroma）不可用时降级返回，不抛异常。"""
        start = time.time()
        filters = filters or {}
        try:
            # 1) 结构化硬约束过滤（RAG 规范第 1 步）
            recipes, _ = RecipeRepository(db).search(
                status="published",
                max_cook_time=filters.get("max_cook_time"),
                tags=filters.get("tags"),
                ingredient_ids=filters.get("ingredient_ids"),
                category_id=filters.get("category_id"),
                household_id=filters.get("household_id"),
                sort="score",
                page=1,
                page_size=_MAX_CANDIDATES,
            )
            candidate_ids = [r.id for r in recipes]
            if not candidate_ids:
                return RetrievalResult(hits=[], total=0, engine_available=True, took_ms=_ms(start))

            # 2) 查询嵌入（失败 → 引擎不可用降级，不中断核心功能）
            try:
                qvec = self.embedding.embed_text(query)
            except EmbeddingUnavailableError as e:
                return RetrievalResult(hits=[], total=0, engine_available=False,
                                       took_ms=_ms(start), error=str(e))

            # 3) 向量召回（限定候选集，默认 Top 20）
            top = self.store.query(qvec, top_k=recall_top_k,
                                   where={"recipe_id": {"$in": candidate_ids}})
            if not top:
                return RetrievalResult(hits=[], total=0, engine_available=True, took_ms=_ms(start))

            recipe_by_id = {r.id: r for r in recipes}

            # 按菜谱聚合命中的多个块（同一道菜的 overview/ingredients/steps 归并）
            chunks_by_recipe: Dict[str, List[dict]] = defaultdict(list)
            for hit in top:
                if hit["recipe_id"] in recipe_by_id:
                    chunks_by_recipe[hit["recipe_id"]].append(hit)

            ing_map = _load_ingredient_names(db, list(chunks_by_recipe.keys()))
            tokens = _keyword_tokens(query)

            # 4) 混合重排（每道菜一个得分：取其最优块的向量分 + 关键词 + 食材）
            scored = []
            for rid, recipe_chunks in chunks_by_recipe.items():
                recipe = recipe_by_id[rid]
                ing_names = ing_map.get(rid, [])
                best_vec = max(c["vector_score"] for c in recipe_chunks)
                kw_score = _keyword_overlap(tokens, recipe.title, recipe.summary)
                ing_score = _ingredient_match(tokens, ing_names)
                score = W_VEC * best_vec + W_KW * kw_score + W_ING * ing_score
                scored.append((score, recipe, ing_names, recipe_chunks))

            scored.sort(key=lambda x: x[0], reverse=True)
            scored = scored[:rerank_top_k]

            # 5) 装配结果（每道菜一条，chunks 携带全部命中块原文，供 C 阶段 LLM 直接消费）
            hits = []
            for score, recipe, ing_names, recipe_chunks in scored:
                matched = [n for n in ing_names if any(t in n for t in tokens)][:5]
                reasons = [f"综合相关度 {score:.2f}"]
                if matched:
                    reasons.append("食材匹配：" + "、".join(matched[:3]))
                chunks = sorted(
                    (
                        {"chunk_type": c["chunk_type"], "text": c["text"],
                         "vector_score": round(c["vector_score"], 4)}
                        for c in recipe_chunks
                    ),
                    key=lambda c: c["vector_score"],
                    reverse=True,
                )
                hits.append(RetrievalHit(
                    recipe_id=recipe.id,
                    title=recipe.title,
                    cover=recipe.cover,
                    summary=recipe.summary,
                    score=round(score, 4),
                    matched_ingredients=matched,
                    reasons=reasons,
                    chunks=chunks,
                ))
            return RetrievalResult(hits=hits, total=len(scored), engine_available=True,
                                   took_ms=_ms(start))
        except EmbeddingUnavailableError as e:
            return RetrievalResult(hits=[], total=0, engine_available=False,
                                   took_ms=_ms(start), error=str(e))
        except Exception as e:  # noqa: BLE001 - Chroma 未就绪等按引擎不可用降级
            return RetrievalResult(hits=[], total=0, engine_available=False,
                                   took_ms=_ms(start), error=f"检索引擎暂不可用: {e}")
