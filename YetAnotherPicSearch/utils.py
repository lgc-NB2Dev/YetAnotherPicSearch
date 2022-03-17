import base64
import re
from io import BytesIO

import httpx
from pyquery import PyQuery


# 将图片转化为 base64
async def get_pic_base64_by_url(url: str, proxy: str) -> str:
    async with httpx.AsyncClient(proxies=proxy) as client:
        r = await client.get(url)
        image_buffer = BytesIO(r.content)
        return str(base64.b64encode(image_buffer.getvalue()), encoding="utf-8")


async def handle_img(url: str, proxy: str, hide_img: bool) -> str:
    if hide_img:
        return ""
    img_base64 = await get_pic_base64_by_url(url, proxy)
    if img_base64:
        return f"[CQ:image,file=base64://{img_base64}]"
    return f"图片下载失败: {url}"


async def get_source(url: str, proxy: str) -> str:
    source = ""
    async with httpx.AsyncClient(proxies=proxy) as client:
        if httpx.URL(url).host == "danbooru.donmai.us":
            source = PyQuery((await client.get(url)).content)(".image-container").attr(
                "data-normalized-source"
            )
        elif httpx.URL(url).host in ["yande.re", "konachan.com"]:
            source = PyQuery((await client.get(url)).content)(
                "#stats li:contains(Source) a"
            ).attr("href")
        elif httpx.URL(url).host == "gelbooru.com":
            source = PyQuery((await client.get(url)).content)(
                "#tag-list li:contains(Source) a"
            ).attr("href")
    if source:
        return str(source)
    return ""


async def shorten_url(url: str) -> str:
    pid_search = re.compile(r"pixiv.+(?:illust_id=|artworks/)([0-9]+)")
    if pid_search.search(url):
        return f"https://pixiv.net/i/{pid_search.search(url).group(1)}"
    if httpx.URL(url).host == "danbooru.donmai.us":
        return url.replace("/post/show/", "/posts/")
    return url
