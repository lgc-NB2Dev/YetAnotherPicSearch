import asyncio
import operator
import re
from collections.abc import Awaitable, Iterable
from contextlib import suppress
from difflib import SequenceMatcher
from functools import wraps
from io import BytesIO
from pathlib import Path
from typing import (
    Callable,
    Optional,
    TypeVar,
    Union,
)
from typing_extensions import ParamSpec

import arrow
from cookit.loguru import logged_suppress
from httpx import URL, AsyncClient, HTTPStatusError, InvalidURL
from nonebot.matcher import current_bot, current_event, current_matcher
from nonebot_plugin_alconna.uniseg import Image as ImageSeg, UniMessage, image_fetch
from PicImageSearch.model.ehentai import EHentaiItem, EHentaiResponse
from PIL import Image
from pyquery import PyQuery
from tenacity import TryAgain, retry, stop_after_attempt, stop_after_delay

from .config import config
from .nhentai_model import NHentaiItem, NHentaiResponse

T = TypeVar("T")
P = ParamSpec("P")


DEFAULT_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/99.0.4844.82 Safari/537.36"
    ),
}


def post_image_process(file: bytes) -> bytes:
    im = Image.open(BytesIO(file))
    if (im.format == "WEBP") or getattr(im, "is_animated", False):
        with BytesIO() as output:
            im.save(output, "PNG")
            return output.getvalue()
    return file


@retry(stop=(stop_after_attempt(3) | stop_after_delay(30)), reraise=True)
async def get_image_bytes_by_url(url: str, cookies: Optional[str] = None) -> bytes:
    _url = URL(url)
    referer = f"{_url.scheme}://{_url.host}/"
    headers = DEFAULT_HEADERS if _url.host.endswith("qpic.cn") else {"Referer": referer, **DEFAULT_HEADERS}
    async with AsyncClient(
        headers=headers,
        cookies=parse_cookies(cookies),
        proxy=config.proxy,
        follow_redirects=True,
    ) as session:
        resp = await session.get(url)
        if resp.status_code == 404:
            resp.raise_for_status()
            raise Exception  # NoReturn for sure, just make linter know
        if resp.status_code >= 400 or len(resp.content) == 0:
            raise TryAgain
        return post_image_process(resp.content)


async def get_image_from_seg(seg: ImageSeg) -> bytes:
    with suppress(ValueError):
        return seg.raw_bytes
    if seg.path:
        return Path(seg.path).read_bytes()
    if file := await image_fetch(
        current_event.get(),
        current_bot.get(),
        current_matcher.get().state,
        seg,
    ):
        return file
    raise ValueError("Cannot get image")


async def handle_img(
    url: str,
    hide_img: bool = config.hide_img,
    cookies: Optional[str] = None,
) -> UniMessage:
    if not hide_img:
        with logged_suppress("Failed to get image", HTTPStatusError):
            return UniMessage.image(raw=await get_image_bytes_by_url(url, cookies))
    return UniMessage.text(f"预览图链接：{url}")


def handle_source(source: str) -> str:
    return (
        source.replace("www.pixiv.net/en/artworks", "www.pixiv.net/artworks")
        .replace(
            "www.pixiv.net/member_illust.php?mode=medium&illust_id=",
            "www.pixiv.net/artworks/",
        )
        .replace("http://", "https://")
    )


def parse_source(resp_text: str, host: str) -> Optional[str]:
    if host in {"danbooru.donmai.us", "gelbooru.com"}:
        source = PyQuery(resp_text)(".image-container").attr("data-normalized-source")
        return str(source) if source else None

    if host in {"yande.re", "konachan.com"}:
        source = PyQuery(resp_text)("#post_source").attr("value")
        pool_text = PyQuery(resp_text)('a[href^="/pool/show/"]').text() or ""
        return str(source) or str(pool_text)

    return ""


async def get_source(url: str) -> str:
    if not url:
        return ""

    _url = get_valid_url(url)
    if not _url:
        return ""

    host = _url.host
    headers = None if host == "danbooru.donmai.us" else DEFAULT_HEADERS
    async with AsyncClient(
        headers=headers,
        proxy=config.proxy,
        follow_redirects=True,
    ) as session:
        resp = await session.get(url)
        if resp.status_code >= 400:
            return ""

        source = parse_source(resp.text, host)
        if source and get_valid_url(source):
            return handle_source(source)

    return source or ""


def confuse_url(url: str) -> str:
    return next(
        (
            url.replace("//", "// ").replace(host, host.replace(".", ". "))
            for host in config.to_confuse_urls
            if host in url
        ),
        url,
    )


async def shorten_url(url: str, force_shorten: bool = False) -> str:
    pid_search = re.compile(
        r"(?:pixiv.+(?:illust_id=|artworks/)|/img-original/img/(?:\d+/){6})(\d+)",
    )
    if pid_match := pid_search.search(url):
        return confuse_url(f"https://pixiv.net/i/{pid_match[1]}")

    uid_search = re.compile(r"pixiv.+(?:member\.php\?id=|users/)(\d+)")
    if uid_match := uid_search.search(url):
        return confuse_url(f"https://pixiv.net/u/{uid_match[1]}")

    host = URL(url).host
    if host == "danbooru.donmai.us":
        return confuse_url(url.replace("/post/show/", "/posts/"))

    if force_shorten or host in {
        "e-hentai.org",
        "exhentai.org",
        "graph.baidu.com",
        "nhentai.net",
        "www.google.com",
        "yandex.com",
    }:
        flag = len(url) > 1024
        async with AsyncClient(headers=DEFAULT_HEADERS) as session:
            if not flag:
                resp = await session.post("https://yww.uy/shorten", json={"url": url})
                if resp.status_code < 400:
                    return resp.json()["url"]
                flag = True
            if flag:
                resp = await session.post(
                    "https://www.shorturl.at/shortener.php",
                    data={"u": url},
                )
                if resp.status_code < 400:
                    final_url = PyQuery(resp.text)("#shortenurl").attr("value")
                    return f"https://{final_url}"

    return confuse_url(url)


def parse_cookies(cookies_str: Optional[str] = None) -> dict[str, str]:
    cookies_dict: dict[str, str] = {}
    if cookies_str:
        for line in cookies_str.split(";"):
            key, value = line.strip().split("=", 1)
            cookies_dict[key] = value
    return cookies_dict


def async_lock(
    freq: float = 1,
) -> Callable[[Callable[P, Awaitable[T]]], Callable[P, Awaitable[T]]]:
    def decorator(func: Callable[P, Awaitable[T]]) -> Callable[P, Awaitable[T]]:
        lock = asyncio.Lock()
        last_call_time: Optional[arrow.Arrow] = None

        @wraps(func)
        async def wrapper(*args: P.args, **kwargs: P.kwargs) -> T:
            nonlocal last_call_time
            async with lock:
                elapsed_time = arrow.now() - (last_call_time or arrow.now().shift(seconds=-freq))
                if elapsed_time.total_seconds() < freq:
                    await asyncio.sleep(freq - elapsed_time.total_seconds())
                result = await func(*args, **kwargs)
                last_call_time = arrow.now()
                return result

        return wrapper

    return decorator


def preprocess_search_query(query: str) -> str:
    query = re.sub(r"●|・|~|～|〜|、|×|:::|\s+-\s+|\[中国翻訳]", " ", query)
    # 去除独立的英文、日文、中文字符，但不去除带连字符的
    for i in [
        r"\b[A-Za-z]\b",
        r"\b[\u4e00-\u9fff]\b",
        r"\b[\u3040-\u309f\u30a0-\u30ff]\b",
    ]:
        query = re.sub(rf"(?<!-){i}(?!-)", "", query)

    return query.strip()


T_Item = TypeVar("T_Item", EHentaiItem, NHentaiItem)
T_Response = TypeVar("T_Response", EHentaiResponse, NHentaiResponse)


def filter_results_with_ratio(
    res: T_Response,
    title: str,
) -> list[T_Item]:
    raw_with_ratio = [(i, SequenceMatcher(lambda x: x == " ", title, i.title).ratio()) for i in res.raw]
    raw_with_ratio.sort(key=operator.itemgetter(1), reverse=True)

    filtered = [i[0] for i in raw_with_ratio if i[1] > 0.65]
    return filtered or [i[0] for i in raw_with_ratio]  # type: ignore


def get_valid_url(url: str) -> Optional[URL]:
    with suppress(InvalidURL):
        url_obj = URL(url)
        if url_obj.host:
            return url_obj
    return None


def combine_message(
    msg_list: Iterable[Union[UniMessage, str, None]],
    join: Optional[str] = "\n",
) -> UniMessage:
    msg = UniMessage()
    for i, it in enumerate(msg_list):
        if not it:
            continue
        if join and i != 0:
            msg += join
        msg += it
    return msg
