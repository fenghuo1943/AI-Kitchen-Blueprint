"""基于 Playwright 的浏览器抓取客户端：用于小红书等登录墙/反爬站点。

Tavily extract 是模拟普通爬虫，登录墙页面拿不到正文。这里用本地浏览器
（launch_persistent_context + 专属 user_data_dir 的持久化登录态）有头抓取，
复用用户在浏览器里登录过的小红书会话。

首次使用：调用 open_login() 打开有头浏览器让用户登录一次，登录态写回 profile，
之后 fetch() 直接复用。所有浏览器操作用模块级锁串行，避免并发启动多个浏览器实例。
有 Chrome/Edge 无需 playwright install；否则需执行 playwright install chromium。
"""
import os
import threading
from contextlib import contextmanager
from typing import Optional, Tuple

from app.core.config import settings
from app.services.tavily_client import clean_page_text


class BrowserFetchError(Exception):
    """浏览器抓取不可用/失败。"""


# Windows 常见 Chrome/Edge 安装路径（探测用，不启动浏览器）
_CHROME_CANDIDATES = (
    r"C:\Program Files\Google\Chrome\Application\chrome.exe",
    r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe",
    os.path.expandvars(r"%LOCALAPPDATA%\Google\Chrome\Application\chrome.exe"),
)
_EDGE_CANDIDATES = (
    r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe",
    r"C:\Program Files\Microsoft\Edge\Application\msedge.exe",
)

# 抓正文时优先尝试的小红书笔记正文选择器；全部失败回落整个页面 innerText
_NOTE_TEXT_SELECTORS = (
    "#detail-desc",
    ".note-content",
    ".note-text",
    "[class*='note-text']",
)


class BrowserFetcher:
    """Playwright 有头浏览器抓取。可注入；测试可替换 _launch_context。"""

    _lock = threading.Lock()

    def __init__(
        self,
        enabled: Optional[bool] = None,
        user_data_dir: Optional[str] = None,
        headed: Optional[bool] = None,
        channel: Optional[str] = None,
        timeout: Optional[int] = None,
    ):
        self._enabled = enabled  # None=运行时取 settings.BROWSER_FETCH_ENABLED（便于测试翻转）
        self._user_data_dir = user_data_dir or settings.BROWSER_USER_DATA_DIR
        self._headed = settings.BROWSER_HEADED if headed is None else headed
        self._channel = channel if channel is not None else settings.BROWSER_CHANNEL
        self._timeout = settings.BROWSER_LAUNCH_TIMEOUT if timeout is None else timeout

    # ------------------------------------------------------------------ #
    # 可用性
    # ------------------------------------------------------------------ #
    def _is_enabled(self) -> bool:
        """总开关：构造时显式传入优先，否则运行时取配置（测试可 monkeypatch settings）。"""
        return settings.BROWSER_FETCH_ENABLED if self._enabled is None else self._enabled

    def available(self) -> Tuple[bool, str]:
        """(是否可用, 原因)。不启动浏览器，只在真正使用时才 launch。"""
        if not self._is_enabled():
            return False, "BROWSER_FETCH_ENABLED 未开启，请在 .env 中设置为 true"
        try:
            import playwright  # noqa: F401
        except ImportError:
            return False, "未安装 playwright（pip install playwright）"
        if not self._resolve_channel():
            return False, "未找到可用的浏览器 channel"
        return True, ""

    def profile_exists(self) -> bool:
        """专属 profile 目录是否已存在（可据此推断是否登录过）。"""
        return os.path.isdir(self._user_data_dir)

    def _resolve_channel(self) -> str:
        """解析要驱动的浏览器 channel：BROWSER_CHANNEL 优先，否则探测本机安装。"""
        if self._channel:
            return self._channel
        if any(os.path.exists(p) for p in _CHROME_CANDIDATES):
            return "chrome"
        if any(os.path.exists(p) for p in _EDGE_CANDIDATES):
            return "msedge"
        return "chromium"

    def _check_available(self) -> None:
        ok, reason = self.available()
        if not ok:
            raise BrowserFetchError(reason)

    # ------------------------------------------------------------------ #
    # 生命周期
    # ------------------------------------------------------------------ #
    @contextmanager
    def _launch_context(self):
        """启动持久化浏览器上下文（有头）。上下文管理器；测试可 monkeypatch 替换。"""
        from playwright.sync_api import sync_playwright

        channel = self._resolve_channel()
        p = sync_playwright().start()
        try:
            context = p.chromium.launch_persistent_context(
                user_data_dir=self._user_data_dir,
                channel=channel if channel != "chromium" else None,
                headless=self._headed,
                args=["--disable-blink-features=AutomationControlled"],
                viewport={"width": 1280, "height": 900},
            )
        except Exception:
            p.stop()
            raise
        try:
            yield context
        finally:
            context.close()
            p.stop()

    # ------------------------------------------------------------------ #
    # 抓取 / 登录
    # ------------------------------------------------------------------ #
    def fetch(self, url: str, timeout: Optional[int] = None) -> str:
        """有头抓取页面正文，返回清洗后的文本；失败/正文为空抛 BrowserFetchError。"""
        self._check_available()
        timeout_ms = timeout or self._timeout
        with BrowserFetcher._lock:
            try:
                with self._launch_context() as context:
                    page = context.new_page()
                    page.goto(url, wait_until="domcontentloaded", timeout=timeout_ms)
                    page.wait_for_timeout(2500)  # 等 JS 渲染正文
                    self._scroll_page(page)
                    text = self._extract_text(page)
            except BrowserFetchError:
                raise
            except Exception as e:  # noqa: BLE001 - 超时/网络/找不到浏览器都归为抓取失败
                raise BrowserFetchError(f"浏览器抓取失败: {e}") from e
        text = clean_page_text(text)
        if not text:
            raise BrowserFetchError("页面正文为空（可能未登录小红书或页面无法访问）")
        return text

    def open_login(self, url: str = "https://www.xiaohongshu.com", wait_seconds: int = 300) -> None:
        """打开有头浏览器让用户登录（阻塞到关窗），登录态写回 profile。"""
        self._check_available()
        with BrowserFetcher._lock:
            try:
                with self._launch_context() as context:
                    page = context.new_page()
                    page.goto(url, wait_until="domcontentloaded", timeout=self._timeout)
                    # 阻塞直到用户关闭窗口；关窗时持久化上下文自动写回登录态
                    context.wait_for_event("close", timeout=wait_seconds * 1000)
            except BrowserFetchError:
                raise
            except Exception as e:  # noqa: BLE001
                raise BrowserFetchError(f"浏览器登录失败: {e}") from e

    # ------------------------------------------------------------------ #
    # 正文提取
    # ------------------------------------------------------------------ #
    @staticmethod
    def _scroll_page(page) -> None:
        """滚动到底部触发懒加载（小红书正文随滚动加载）。失败静默忽略。"""
        try:
            page.evaluate(
                "async () => { for (let i = 0; i < 5; i++) { "
                "window.scrollBy(0, document.body.scrollHeight); "
                "await new Promise(r => setTimeout(r, 300)); } }"
            )
        except Exception:  # noqa: BLE001
            pass

    @staticmethod
    def _extract_text(page) -> str:
        """优先候选选择器取正文，回落 body innerText。"""
        for selector in _NOTE_TEXT_SELECTORS:
            try:
                handles = page.query_selector_all(selector)
                if handles:
                    texts = [h.inner_text() for h in handles]
                    joined = "\n".join(t for t in texts if t.strip())
                    if joined.strip():
                        return joined
            except Exception:  # noqa: BLE001
                continue
        try:
            return page.evaluate("() => document.body ? document.body.innerText : ''")
        except Exception:  # noqa: BLE001
            return ""
