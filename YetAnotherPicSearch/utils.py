import base64
import re
from typing import Optional

import aiohttp
from pyquery import PyQuery
from yarl import URL


# 将图片转化为 base64
async def get_pic_base64_by_url(
    url: str, proxy: Optional[str], cookies: Optional[str] = None
) -> str:
    headers = {}
    if cookies:
        headers["Cookie"] = cookies
    async with aiohttp.ClientSession(headers=headers) as session:
        async with session.get(url, proxy=proxy) as resp:
            if resp.status == 200:
                return base64.b64encode(await resp.read()).decode()
    return ""


async def handle_img(
    url: str, proxy: Optional[str], hide_img: bool, cookies: Optional[str] = None
) -> str:
    if hide_img:
        return ""
    img_base64 = await get_pic_base64_by_url(url, proxy, cookies)
    if img_base64:
        return f"[CQ:image,file=base64://{img_base64}]"
    return f"图片下载失败: {url}"


async def get_source(url: str, proxy: Optional[str]) -> str:
    source = ""
    async with aiohttp.ClientSession() as session:
        if URL(url).host == "danbooru.donmai.us":
            async with session.get(url, proxy=proxy) as resp:
                if resp.status == 200:
                    html = await resp.text()
                    source = PyQuery(html)(".image-container").attr(
                        "data-normalized-source"
                    )
        elif URL(url).host in ["yande.re", "konachan.com"]:
            async with session.get(url, proxy=proxy) as resp:
                if resp.status == 200:
                    html = await resp.text()
                    source = PyQuery(html)("#stats li:contains(Source) a").attr("href")
        elif URL(url).host == "gelbooru.com":
            async with session.get(url, proxy=proxy) as resp:
                if resp.status == 200:
                    html = await resp.text()
                    source = PyQuery(html)("#tag-list li:contains(Source) a").attr(
                        "href"
                    )
    return str(source)


def shorten_url(url: str) -> str:
    pid_search = re.compile(
        r"(?:pixiv.+(?:illust_id=|artworks/)|/img-original/img/(?:\d+/){6})(\d+)"
    )
    if pid_search.search(url):
        return f"https://pixiv.net/i/{pid_search.search(url)[1]}"  # type: ignore
    if URL(url).host == "danbooru.donmai.us":
        return url.replace("/post/show/", "/posts/")
    return url
