import asyncio
import importlib.util
import os
from pathlib import Path

import pytest

from weread_exporter import utils
from weread_exporter.webpage import WeReadWebPage


def load_mcp_server():
    path = Path(__file__).parents[1] / ".claude-plugin" / "mcp_server.py"
    spec = importlib.util.spec_from_file_location("weread_mcp_server", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@pytest.mark.parametrize(
    "url",
    [
        "https://weread.qq.com/web/bookDetail/abc123",
        "https://cdn.weread.qq.com/web/app.js",
        "https://images.cdn.weread.qq.com/cover.jpg",
    ],
)
def test_weread_url_allowlist_accepts_official_hosts(url):
    assert utils.validate_weread_url(url).hostname.endswith("weread.qq.com")


@pytest.mark.parametrize(
    "url",
    [
        "http://weread.qq.com/",
        "https://weread.qq.com.evil.example/",
        "https://evilweread.qq.com.example/",
        "https://user:password@weread.qq.com/",
        "file:///etc/passwd",
    ],
)
def test_weread_url_allowlist_rejects_unsafe_destinations(url):
    with pytest.raises(ValueError):
        utils.validate_weread_url(url)


@pytest.mark.parametrize("book_id", ["../secret", "/tmp/secret", "a.b", "", None])
def test_book_id_rejects_path_traversal(book_id):
    with pytest.raises(ValueError):
        utils.validate_book_id(book_id)


def test_cookie_file_is_private(tmp_path):
    private_dir = tmp_path / "state"
    page = WeReadWebPage(
        "08232ac0720befa90825d88",
        cookie_path=str(private_dir / "cookie.json"),
        webcache_path=str(private_dir / "cache"),
    )
    page._cookie = {"wr_vid": "secret-value"}
    page._save_cookie()
    assert os.stat(private_dir / "cookie.json").st_mode & 0o777 == 0o600


def test_cookie_is_only_attached_to_primary_host(tmp_path):
    page = WeReadWebPage(
        "08232ac0720befa90825d88",
        cookie_path=str(tmp_path / "cookie.json"),
        webcache_path=str(tmp_path / "cache"),
    )
    page._cookie = {"wr_vid": "secret-value"}
    primary = page._handle_request_headers("https://weread.qq.com/web/user", {})
    cdn = page._handle_request_headers(
        "https://cdn.weread.qq.com/app.js", {"cookie": "browser-cookie"}
    )
    assert "secret-value" in primary["cookie"]
    assert "cookie" not in cdn


def test_resource_cache_rejects_encoded_parent_segments(tmp_path):
    page = WeReadWebPage(
        "08232ac0720befa90825d88",
        cookie_path=str(tmp_path / "cookie.json"),
        webcache_path=str(tmp_path / "cache"),
    )
    with pytest.raises(ValueError, match="Unsafe resource path"):
        asyncio.run(
            page._get_from_cache_or_server(
                "https://cdn.weread.qq.com/%2e%2e/%2e%2e/escape.js"
            )
        )


def test_mcp_redacts_secrets_and_rejects_unsafe_arguments():
    mcp_server = load_mcp_server()
    sanitized = mcp_server.sanitize_output(
        "cookie=abc123 wr_vid: xyz987 token=topsecret"
    )
    assert "abc123" not in sanitized
    assert "xyz987" not in sanitized
    assert "topsecret" not in sanitized
    result = asyncio.run(mcp_server.export_weread_book({"book_id": "../../bad"}))
    assert result.startswith("Error:")
    result = asyncio.run(
        mcp_server.export_weread_book({"book_id": "abc123", "formats": ["pdf"]})
    )
    assert result.startswith("Error:")
