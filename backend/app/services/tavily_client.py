"""Tavily 联网搜索/抽取客户端。

search 返回候选网页（标题/URL/摘要）；extract 抓取并清洗网页正文。
任一失败抛 TavilyUnavailableError，采集任务据此降级（不中断核心功能）。
"""
import re
from dataclasses import dataclass
from typing import List, Optional, Tuple

import httpx

from app.core.config import settings


class TavilyUnavailableError(Exception):
    """Tavily 未配置 / 不可达 / key 失效。"""


@dataclass
class TavilySearchResult:
    title: str
    url: str
    content: str
    score: float
    published_date: Optional[str] = None


def clean_page_text(raw: str) -> str:
    """清洗网页正文：去 HTML 标签/控制字符、折叠空白、截断。"""
    text = raw or ""
    text = re.sub(r"<[^>]+>", " ", text)  # 去 HTML 标签
    text = re.sub(r"[\x00-\x08\x0b\x0c\x0e-\x1f]", " ", text)  # 去控制字符
    text = re.sub(r"\s+", " ", text).strip()  # 折叠空白
    return text[: settings.AI_COLLECT_PAGE_CHARS]


class TavilyClient:
    """Tavily 客户端。api_key 未配置时抛 TavilyUnavailableError。"""

    def __init__(
        self,
        api_key: Optional[str] = settings.TAVILY_API_KEY,
        base_url: str = settings.TAVILY_BASE_URL,
        timeout: int = settings.TAVILY_TIMEOUT,
    ):
        self._api_key = api_key
        self._client = httpx.Client(base_url=base_url, timeout=timeout)

    def _headers(self) -> dict:
        if not self._api_key:
            raise TavilyUnavailableError("TAVILY_API_KEY 未配置，请先在 .env 中填写")
        return {
            "Authorization": f"Bearer {self._api_key}",
            "Content-Type": "application/json",
        }

    def search(self, query: str, max_results: int = 5, search_depth: str = "basic") -> List[TavilySearchResult]:
        """联网搜索，返回候选结果列表。"""
        try:
            resp = self._client.post(
                "/search",
                headers=self._headers(),
                json={
                    "query": query,
                    "search_depth": search_depth,
                    "max_results": max_results,
                    "include_answer": False,
                    "include_raw_content": False,
                },
            )
            resp.raise_for_status()
        except httpx.HTTPError as e:
            raise TavilyUnavailableError(f"Tavily 搜索失败: {e}") from e

        data = resp.json()
        results = []
        for item in data.get("results", []):
            results.append(
                TavilySearchResult(
                    title=item.get("title", ""),
                    url=item.get("url", ""),
                    content=item.get("content", ""),
                    score=float(item.get("score", 0.0)),
                    published_date=item.get("published_date"),
                )
            )
        return results

    def extract(self, urls: List[str]) -> Tuple[List[dict], List[dict]]:
        """抓取网页正文。返回 (results:[{url,raw_content,metadata}], failed_results:[{url,error}])。"""
        if not urls:
            return [], []
        try:
            resp = self._client.post(
                "/extract",
                headers=self._headers(),
                json={"urls": urls, "include_images": False, "extract_depth": "basic"},
            )
            resp.raise_for_status()
        except httpx.HTTPError as e:
            raise TavilyUnavailableError(f"Tavily 抽取失败: {e}") from e

        data = resp.json()
        results = [
            {"url": r.get("url"), "raw_content": r.get("raw_content", ""), "metadata": r.get("metadata", {})}
            for r in data.get("results", [])
        ]
        failed = [
            {"url": f.get("url"), "error": f.get("error", "")}
            for f in data.get("failed_results", [])
        ]
        return results, failed
