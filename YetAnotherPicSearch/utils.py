import base64
from io import BytesIO

import httpx
from pyquery import PyQuery


# 将图片转化为 base64
async def get_pic_base64_by_url(url: str, proxy: str) -> str:
    async with httpx.AsyncClient(proxies=proxy):
        r = httpx.get(url)
        image_buffer = BytesIO(r.content)
        res = str(base64.b64encode(image_buffer.getvalue()), encoding="utf-8")
        return res


async def handle_img(url: str, proxy: str, hide_img: bool) -> str:
    if hide_img:
        return ""
    img_base64 = await get_pic_base64_by_url(url, proxy)
    if img_base64:
        return f"[CQ:image,file=base64://{img_base64}]"
    return f"图片下载失败: {url}"


async def get_source(url: str, proxy: str) -> str:
    async with httpx.AsyncClient(proxies=proxy) as client:
        if "danbooru.donmai.us" in url:
            return PyQuery((await client.get(url)).content)(".image-container").attr(
                "data-normalized-source"
            )
        elif "konachan.com" in url or "yande.re" in url:
            return PyQuery((await client.get(url)).content)(
                "#stats li:contains(Source) a"
            ).attr("href")
        elif "gelbooru.com" in url:
            return PyQuery((await client.get(url)).content)(
                "#tag-list li:contains(Source) a"
            ).attr("href")
    return ""
