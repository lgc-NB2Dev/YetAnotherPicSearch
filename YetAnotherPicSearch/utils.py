import re
from base64 import b64encode
from difflib import SequenceMatcher
from typing import (
    Any,
    Callable,
    Coroutine,
    Dict,
    List,
    Optional,
    Union,
)

from cachetools import TTLCache
from httpx import URL, AsyncClient
from nonebot.adapters.onebot.v11 import Bot
from PicImageSearch.model.ehentai import EHentaiItem, EHentaiResponse
from pyquery import PyQuery
from shelved_cache import cachedasyncmethod

from .config import config
from .nhentai_model import NHentaiItem, NHentaiResponse

SEARCH_FUNCTION_TYPE = Callable[..., Coroutine[Any, Any, List[str]]]

DEFAULT_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/99.0.4844.82 Safari/537.36"
    )
}


async def get_image_bytes_by_url(
    url: str, cookies: Optional[str] = None
) -> Optional[bytes]:
    async with AsyncClient(
        headers=DEFAULT_HEADERS,
        cookies=parse_cookies(cookies),
        proxies=config.proxy,
        follow_redirects=True,
    ) as session:
        resp = await session.get(url)
        if resp.status_code < 400:
            return resp.content
    return None


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


async def get_source(url: str) -> str:
    source = url
    if host := URL(source).host:
        headers = None if host == "danbooru.donmai.us" else DEFAULT_HEADERS
        async with AsyncClient(
            headers=headers, proxies=config.proxy, follow_redirects=True
        ) as session:
            resp = await session.get(source)
            if resp.status_code >= 400:
                return ""

            if host in ["danbooru.donmai.us", "gelbooru.com"]:
                source = PyQuery(resp.text)(".image-container").attr(
                    "data-normalized-source"
                )

            elif host in ["yande.re", "konachan.com"]:
                source = PyQuery(resp.text)("#post_source").attr("value")
                if not source:
                    source = PyQuery(resp.text)('a[href^="/pool/show/"]').text()

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

    if URL(url).host == "danbooru.donmai.us":
        return confuse_url(url.replace("/post/show/", "/posts/"))

    if URL(url).host in [
        "exhentai.org",
        "e-hentai.org",
        "nhentai.net",
        "graph.baidu.com",
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


def preprocess_search_query(query: str) -> str:
    query = re.sub(r"●|・|~|～|〜|、|×|:::|\s+-\s+|\[中国翻訳]", " ", query)
    # 去除独立的英文、日文、中文字符
    for i in [
        r"\b[A-Za-z]\b",
        r"\b[\u4e00-\u9fff]\b",
        r"\b[\u3040-\u309f\u30a0-\u30ff]\b",
    ]:
        query = re.sub(i, "", query)

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
