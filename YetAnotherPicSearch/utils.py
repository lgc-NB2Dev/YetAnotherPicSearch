import re
from base64 import b64encode
from typing import Any, Callable, Coroutine, Dict, List, Optional

from aiohttp import ClientSession, TCPConnector
from cachetools import TTLCache
from nonebot.adapters.onebot.v11 import Bot
from pyquery import PyQuery
from shelved_cache import cachedasyncmethod
from yarl import URL

from .config import config

SEARCH_FUNCTION_TYPE = Callable[..., Coroutine[Any, Any, List[str]]]

DEFAULT_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/99.0.4844.82 Safari/537.36"
    )
}


def get_session_with_proxy(headers: Optional[Dict[str, str]] = None) -> ClientSession:
    if config.proxy and config.proxy.startswith("socks"):
        try:
            from aiohttp_socks import ProxyConnector

            connector = ProxyConnector.from_url(config.proxy)
        except ModuleNotFoundError:
            connector = TCPConnector()
    else:
        connector = TCPConnector()

    session = ClientSession(connector=connector, headers=headers)

    if config.proxy and not config.proxy.startswith("socks"):
        from functools import partial

        session.get = partial(session.get, proxy=config.proxy)  # type: ignore
        session.post = partial(session.post, proxy=config.proxy)  # type: ignore

    return session


async def get_image_bytes_by_url(
    url: str, cookies: Optional[str] = None
) -> Optional[bytes]:
    headers = {"Cookie": cookies, **DEFAULT_HEADERS} if cookies else DEFAULT_HEADERS
    async with get_session_with_proxy(headers=headers) as session:
        async with session.get(url) as resp:
            if resp.status < 400 and (image_bytes := await resp.read()):
                return image_bytes
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
        async with get_session_with_proxy(
            headers=None if host == "danbooru.donmai.us" else DEFAULT_HEADERS
        ) as session:
            async with session.get(source) as resp:
                if resp.status >= 400:
                    return ""

                html = await resp.text()
                if host in ["danbooru.donmai.us", "gelbooru.com"]:
                    source = PyQuery(html)(".image-container").attr(
                        "data-normalized-source"
                    )

                elif host in ["yande.re", "konachan.com"]:
                    source = PyQuery(html)("#post_source").attr("value")
                    if not source:
                        source = PyQuery(html)('a[href^="/pool/show/"]').text()

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
        async with ClientSession(headers=DEFAULT_HEADERS) as session:
            if not flag:
                resp = await session.post("https://yww.uy/shorten", json={"url": url})
                if resp.status < 400:
                    return (await resp.json())["url"]  # type: ignore
                else:
                    flag = True
            if flag:
                resp = await session.post(
                    "https://www.shorturl.at/shortener.php", data={"u": url}
                )
                if resp.status < 400:
                    html = await resp.text()
                    final_url = PyQuery(html)("#shortenurl").attr("value")
                    return f"https://{final_url}"

    return confuse_url(url)
