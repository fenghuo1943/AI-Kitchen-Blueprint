"""BrowserFetcher（Playwright 浏览器抓取）单元测试。

不启动真实浏览器：monkeypatch _launch_context 为返回 FakeContext 的上下文管理器，
验证可用性判断、channel 探测、抓取正文清洗与空正文报错。
"""
import builtins
import os
from contextlib import contextmanager

import pytest

from app.services.browser_fetcher import BrowserFetchError, BrowserFetcher


class FakePage:
    """记录 goto，evaluate/query_selector 返回可配置正文。"""

    def __init__(self, text="凉拌黄瓜\n做法：黄瓜拍碎、蒜末、生抽醋拌匀"):
        self.text = text
        self.goto_calls = 0

    def goto(self, url, wait_until=None, timeout=None):
        self.goto_calls += 1

    def wait_for_timeout(self, ms):
        pass

    def query_selector_all(self, selector):
        return []

    def evaluate(self, expr):
        return self.text


class FakeContext:
    def __init__(self, page=None):
        self.page = page or FakePage()
        self.close_called = False

    def new_page(self):
        return self.page

    def wait_for_event(self, event, timeout=None):
        self.close_called = True  # 模拟用户关闭窗口
        return None

    def close(self):
        self.close_called = True


def _patch_launch(monkeypatch, ctx):
    @contextmanager
    def _fake(_self):
        yield ctx

    monkeypatch.setattr(BrowserFetcher, "_launch_context", _fake)


def test_fetch_returns_cleaned_text(monkeypatch):
    ctx = FakeContext(page=FakePage(text="  凉拌黄瓜 \n\n 做法：黄瓜拍碎、蒜末 \n  "))
    _patch_launch(monkeypatch, ctx)
    fetcher = BrowserFetcher(enabled=True, channel="chromium")

    result = fetcher.fetch("https://xhslink.com/a/bC1D")

    assert "凉拌黄瓜" in result
    assert "黄瓜拍碎" in result
    assert ctx.page.goto_calls == 1
    assert "\n\n" not in result  # 空白被折叠


def test_fetch_empty_text_raises(monkeypatch):
    _patch_launch(monkeypatch, FakeContext(page=FakePage(text="")))
    fetcher = BrowserFetcher(enabled=True, channel="chromium")

    with pytest.raises(BrowserFetchError):
        fetcher.fetch("https://xhslink.com/a/bC1D")


def test_fetch_when_disabled_raises():
    fetcher = BrowserFetcher(enabled=False)

    with pytest.raises(BrowserFetchError):
        fetcher.fetch("https://xhslink.com/a/bC1D")


def test_available_disabled():
    ok, reason = BrowserFetcher(enabled=False).available()
    assert ok is False
    assert "BROWSER_FETCH_ENABLED" in reason


def test_available_no_playwright(monkeypatch):
    real_import = builtins.__import__

    def fake_import(name, *args, **kwargs):
        if name == "playwright":
            raise ImportError("No module named 'playwright'")
        return real_import(name, *args, **kwargs)

    monkeypatch.setattr(builtins, "__import__", fake_import)
    ok, reason = BrowserFetcher(enabled=True, channel="chromium").available()
    assert ok is False
    assert "playwright" in reason


def test_available_default_uses_settings_enabled(monkeypatch):
    monkeypatch.setattr("app.core.config.settings.BROWSER_FETCH_ENABLED", False)
    ok, _reason = BrowserFetcher(channel="chromium").available()
    assert ok is False


def test_resolve_channel_prefers_chrome(monkeypatch):
    chrome = r"C:\Program Files\Google\Chrome\Application\chrome.exe"
    monkeypatch.setattr(os.path, "exists", lambda p: p == chrome)
    assert BrowserFetcher(enabled=True, channel="")._resolve_channel() == "chrome"


def test_resolve_channel_falls_back_to_edge(monkeypatch):
    edge = r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe"
    monkeypatch.setattr(
        os.path, "exists",
        lambda p: p.startswith(r"C:\Program Files (x86)\Microsoft\Edge"),
    )
    assert BrowserFetcher(enabled=True, channel="")._resolve_channel() == "msedge"


def test_resolve_channel_no_browser_returns_chromium(monkeypatch):
    monkeypatch.setattr(os.path, "exists", lambda p: False)
    assert BrowserFetcher(enabled=True, channel="")._resolve_channel() == "chromium"


def test_resolve_channel_explicit_wins():
    assert BrowserFetcher(enabled=True, channel="msedge")._resolve_channel() == "msedge"


def test_open_login_waits_until_window_closed(monkeypatch):
    ctx = FakeContext(page=FakePage())
    _patch_launch(monkeypatch, ctx)
    fetcher = BrowserFetcher(enabled=True, channel="chromium")

    fetcher.open_login("https://www.xiaohongshu.com", wait_seconds=5)

    assert ctx.page.goto_calls == 1
    assert ctx.close_called is True
