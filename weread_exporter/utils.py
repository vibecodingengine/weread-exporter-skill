"""Security-conscious helpers for the WeRead exporter."""

import asyncio
import hashlib
import logging
import re
import secrets
import urllib.parse

import aiohttp


MAX_RESPONSE_BYTES = 64 * 1024 * 1024
BOOK_ID_RE = re.compile(r"^[A-Za-z0-9_-]{1,128}$")


class ChromeNotInstalledError(Exception):
    pass


class LoginRequiredError(RuntimeError):
    pass


class LoadChapterFailedError(RuntimeError):
    pass


class InvalidUserError(RuntimeError):
    pass


def is_allowed_weread_host(hostname):
    """Return true only for official WeRead hosts and their subdomains."""
    hostname = (hostname or "").lower().rstrip(".")
    return hostname == "weread.qq.com" or hostname.endswith(".weread.qq.com")


def validate_weread_url(url):
    """Reject non-HTTPS and non-WeRead destinations before any request is sent."""
    parsed = urllib.parse.urlsplit(url)
    if parsed.scheme != "https" or not is_allowed_weread_host(parsed.hostname):
        raise ValueError("Blocked non-WeRead URL: %s" % url)
    if parsed.username or parsed.password:
        raise ValueError("Credentials in URLs are not allowed")
    return parsed


def validate_book_id(book_id):
    if not isinstance(book_id, str) or not BOOK_ID_RE.fullmatch(book_id):
        raise ValueError(
            "book_id must contain only letters, digits, '_' or '-' (max 128 chars)"
        )
    return book_id


def validate_path_component(value, name="path component"):
    if not isinstance(value, (str, int)):
        raise ValueError("%s has an invalid type" % name)
    value = str(value)
    if not BOOK_ID_RE.fullmatch(value):
        raise ValueError("Invalid %s" % name)
    return value


def generate_user_agent():
    user_agent_tmpl = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/%d.0.0.0 Safari/537.36"
    return user_agent_tmpl % (120 + secrets.randbelow(21))


async def fetch(url, method="GET", headers=None, data=None, respond_with_headers=False):
    """Fetch a bounded response from an official WeRead HTTPS endpoint.

    Redirects are followed manually so every destination is checked against the
    same allowlist. Sensitive headers cannot be forwarded cross-origin because
    cross-origin destinations are rejected.
    """
    headers = dict(headers or {})
    headers.pop("sec-ch-ua", None)
    headers.pop("sec-ch-ua-platform", None)
    if data and not isinstance(data, bytes):
        data = data.encode("utf-8")

    timeout = aiohttp.ClientTimeout(total=120, connect=20, sock_read=60)
    current_url = url
    current_method = method.upper()
    current_data = data
    async with aiohttp.ClientSession(timeout=timeout, auto_decompress=True) as session:
        for redirect_count in range(4):
            validate_weread_url(current_url)
            request_method = getattr(session, current_method.lower(), None)
            if request_method is None:
                raise ValueError("Unsupported HTTP method: %s" % current_method)
            try:
                async with request_method(
                    current_url,
                    headers=headers,
                    data=current_data,
                    allow_redirects=False,
                ) as response:
                    if response.status in (301, 302, 303, 307, 308):
                        if redirect_count >= 3:
                            raise RuntimeError("Too many redirects")
                        location = response.headers.get("Location")
                        if not location:
                            raise RuntimeError("Redirect response has no Location")
                        current_url = urllib.parse.urljoin(current_url, location)
                        validate_weread_url(current_url)
                        if response.status == 303 or (
                            response.status in (301, 302) and current_method == "POST"
                        ):
                            current_method = "GET"
                            current_data = None
                        continue

                    declared_size = response.content_length
                    if declared_size is not None and declared_size > MAX_RESPONSE_BYTES:
                        raise RuntimeError("Response is too large")
                    chunks = []
                    total = 0
                    async for chunk in response.content.iter_chunked(64 * 1024):
                        total += len(chunk)
                        if total > MAX_RESPONSE_BYTES:
                            raise RuntimeError("Response exceeded size limit")
                        chunks.append(chunk)
                    result = b"".join(chunks)
                    if respond_with_headers:
                        return response.status, response.headers, result
                    return result
            except (aiohttp.ClientError, asyncio.TimeoutError):
                logging.exception("Fetch from allowed WeRead endpoint failed")
                if redirect_count >= 2:
                    raise
        raise RuntimeError("Fetch failed")


async def get_book_list(book_list_id):
    validate_book_id(book_list_id)
    book_list = []
    url = "https://weread.qq.com/misc/booklist/" + book_list_id
    html = (await fetch(url)).decode()
    pos = html.find("window.__NUXT__")
    if pos <= 0:
        raise RuntimeError("Unexpected book-list response")
    pos = html.find("bookEntities:", pos)
    while True:
        if book_list:
            pos = html.find('},"', pos)
            if pos < 0:
                break
        pos = html.find('"', pos)
        pos1 = html.find('"', pos + 1)
        book_id = html[pos + 1 : pos1]
        pos = html.find("title:", pos)
        pos = html.find('"', pos)
        pos1 = html.find('"', pos + 1)
        title = html[pos + 1 : pos1]
        book_list.append({"id": wr_hash(book_id), "title": title})
    return book_list


def format_filename(filename):
    filename = re.sub(r"[\\/\x00-\x1f\x7f:]+", "_", str(filename)).strip(" .")
    return filename[:180] or "untitled"


def md5(s):
    if not isinstance(s, bytes):
        s = s.encode()
    return hashlib.md5(s, usedforsecurity=False).hexdigest()


def wr_hash(s):
    hash_value = md5(s)
    result = hash_value[:3] + "32" + hash_value[-2:]
    encoded_parts = []
    for i in range(0, len(s), 9):
        encoded_parts.append("%x" % int(s[i : min(i + 9, len(s))]))
    for i, item in enumerate(encoded_parts):
        length = "%x" % len(item)
        result += length.zfill(2) + item
        if i < len(encoded_parts) - 1:
            result += "g"
    if len(result) < 20:
        result += hash_value[: 20 - len(result)]
    result += hashlib.md5(result.encode(), usedforsecurity=False).hexdigest()[:3]
    return result


def save_to_png(img_path, png_path):
    from PIL import Image

    img = Image.open(img_path)
    img.save(png_path)
