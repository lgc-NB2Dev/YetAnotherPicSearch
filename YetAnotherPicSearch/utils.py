import asyncio
import re
from base64 import b64encode
from collections import defaultdict
from difflib import SequenceMatcher
from functools import wraps
from io import BytesIO
from typing import (
    Any,
    Callable,
    Coroutine,
    DefaultDict,
    Dict,
    List,
    Optional,
    TypeVar,
    Union,
)

import arrow
from cachetools import TTLCache
from httpx import URL, AsyncClient, InvalidURL
from nonebot.adapters.onebot.v11 import Bot
from PicImageSearch.model.ehentai import EHentaiItem, EHentaiResponse
from PIL import Image
from pyquery import PyQuery
from shelved_cache import cachedasyncmethod
from tenacity import TryAgain, retry, stop_after_attempt, stop_after_delay

from .config import config
from .nhentai_model import NHentaiItem, NHentaiResponse

T = TypeVar("T")
SEARCH_FUNCTION_TYPE = Callable[..., Coroutine[Any, Any, List[str]]]

DEFAULT_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/99.0.4844.82 Safari/537.36"
    )
}


@retry(stop=(stop_after_attempt(3) | stop_after_delay(30)), reraise=True)
async def get_image_bytes_by_url(
    url: str, cookies: Optional[str] = None
) -> Optional[bytes]:
    _url = URL(url)
    referer = f"{_url.scheme}://{_url.host}/"
    headers = (
        DEFAULT_HEADERS
        if _url.host.endswith("qpic.cn")
        else {"Referer": referer, **DEFAULT_HEADERS}
    )
    async with AsyncClient(
        headers=headers,
        cookies=parse_cookies(cookies),
        proxies=config.proxy,
        follow_redirects=True,
    ) as session:
        resp = await session.get(url)
        if resp.status_code == 404:
            return None

        if resp.status_code >= 400 or len(resp.content) == 0:
            raise TryAgain

        im = Image.open(BytesIO(resp.content))
        if im.format == "WEBP":
            with BytesIO() as output:
                im.save(output, "PNG")
                return output.getvalue()

    return resp.content


async def handle_img(
    url: str,
    hide_img: bool = config.hide_img,
    cookies: Optional[str] = None,
) -> str:
    if not hide_img:
        if image_bytes := await get_image_bytes_by_url(url, cookies):
            return f"[CQ:image,file=base64://{b64encode(image_bytes).decode()}]"
    return f"预览图链接：{url}"


@cachedasyncmethod(lambda self: TTLCache(1, 300))  # type: ignore
async def get_bot_friend_list(bot: Bot) -> List[int]:
    friend_list = await bot.get_friend_list()
    return [i["user_id"] for i in friend_list]


def handle_reply_msg(message_id: int) -> str:
    return f"[CQ:reply,id={message_id}]"


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
    if host in ["danbooru.donmai.us", "gelbooru.com"]:
        return PyQuery(resp_text)(".image-container").attr("data-normalized-source")

    elif host in ["yande.re", "konachan.com"]:
        source = PyQuery(resp_text)("#post_source").attr("value")
        return source or PyQuery(resp_text)('a[href^="/pool/show/"]').text()

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
        headers=headers, proxies=config.proxy, follow_redirects=True
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


async def shorten_url(url: str) -> str:
    pid_search = re.compile(
        r"(?:pixiv.+(?:illust_id=|artworks/)|/img-original/img/(?:\d+/){6})(\d+)"
    )
    if pid_match := pid_search.search(url):
        return confuse_url(f"https://pixiv.net/i/{pid_match[1]}")

    uid_search = re.compile(r"pixiv.+(?:member\.php\?id=|users/)(\d+)")
    if uid_match := uid_search.search(url):
        return confuse_url(f"https://pixiv.net/u/{uid_match[1]}")

    host = URL(url).host
    if host == "danbooru.donmai.us":
        return confuse_url(url.replace("/post/show/", "/posts/"))

    elif host in [
        "e-hentai.org",
        "exhentai.org",
        "graph.baidu.com",
        "nhentai.net",
        "www.google.com",
        "yandex.com",
    ]:
        flag = len(url) > 1024
        async with AsyncClient(headers=DEFAULT_HEADERS) as session:
            if not flag:
                resp = await session.post("https://yww.uy/shorten", json={"url": url})
                if resp.status_code < 400:
                    return resp.json()["url"]  # type: ignore
                else:
                    flag = True
            if flag:
                resp = await session.post(
                    "https://www.shorturl.at/shortener.php", data={"u": url}
                )
                if resp.status_code < 400:
                    final_url = PyQuery(resp.text)("#shortenurl").attr("value")
                    return f"https://{final_url}"

    return confuse_url(url)


def parse_cookies(cookies_str: Optional[str] = None) -> Dict[str, str]:
    cookies_dict: Dict[str, str] = {}
    if cookies_str:
        for line in cookies_str.split(";"):
            key, value = line.strip().split("=", 1)
            cookies_dict[key] = value
    return cookies_dict


def async_lock(
    freq: float = 1,
) -> Callable[
    [Callable[..., Coroutine[Any, Any, T]]], Callable[..., Coroutine[Any, Any, T]]
]:
    def decorator(
        func: Callable[..., Coroutine[Any, Any, T]]
    ) -> Callable[..., Coroutine[Any, Any, T]]:
        locks: DefaultDict[str, asyncio.Lock] = defaultdict(asyncio.Lock)
        call_times: DefaultDict[str, arrow.Arrow] = defaultdict(
            lambda: arrow.now().shift(seconds=-freq)
        )

        @wraps(func)
        async def wrapper(*args: Any, **kwargs: Any) -> T:
            async with locks[func.__name__]:
                last_call_time = call_times[func.__name__]
                elapsed_time = arrow.now() - last_call_time
                if elapsed_time.total_seconds() < freq:
                    await asyncio.sleep(freq - elapsed_time.total_seconds())
                result = await func(*args, **kwargs)
                call_times[func.__name__] = arrow.now()
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


def filter_results_with_ratio(
    res: Union[EHentaiResponse, NHentaiResponse], title: str
) -> Union[List[EHentaiItem], List[NHentaiItem]]:
    raw_with_ratio = [
        (i, SequenceMatcher(lambda x: x == " ", title, i.title).ratio())
        for i in res.raw
    ]
    raw_with_ratio.sort(key=lambda x: x[1], reverse=True)

    if filtered := [i[0] for i in raw_with_ratio if i[1] > 0.65]:
        return filtered

    return [i[0] for i in raw_with_ratio]


def get_valid_url(url: str) -> Optional[URL]:
    try:
        url = URL(url)
        if url.host:
            return url
    except InvalidURL:
        return None
    return None
