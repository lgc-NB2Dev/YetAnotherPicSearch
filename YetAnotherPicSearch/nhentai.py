from typing import List

import arrow
from httpx import AsyncClient
from lxml.html import HTMLParser, fromstring
from pyquery import PyQuery

from .config import config
from .utils import handle_img, parse_cookies, preprocess_search_query, shorten_url

NHENTAI_HEADERS = (
    {
        "User-Agent": config.nhentai_useragent,
    }
    if config.nhentai_cookies and config.nhentai_useragent
    else None
)
NHENTAI_COOKIES = parse_cookies(config.nhentai_cookies)


class NHentaiItem:
    def __init__(self, data: PyQuery):
        self.origin: PyQuery = data  # 原始数据
        self.title: str = data.find(".caption").text()
        cover = data.find(".cover")
        self.url: str = f'https://nhentai.net{cover.attr("href")}'
        self.thumbnail: str = cover.find("img").attr("data-src")
        self.type: str = ""
        self.date: str = ""
        self.tags: List[str] = []


class NHentaiResponse:
    def __init__(self, resp_text: str, resp_url: str):
        self.origin: str = resp_text  # 原始数据
        uft8_parser = HTMLParser(encoding="utf-8")
        data = PyQuery(fromstring(self.origin, parser=uft8_parser))
        self.raw: List[NHentaiItem] = [
            NHentaiItem(i) for i in data.find(".gallery").items()
        ]
        self.url: str = resp_url


async def update_nhentai_info(item: NHentaiItem) -> None:
    async with AsyncClient(
        headers=NHENTAI_HEADERS, cookies=NHENTAI_COOKIES, proxies=config.proxy
    ) as session:
        resp = await session.get(item.url)
        uft8_parser = HTMLParser(encoding="utf-8")
        data = PyQuery(fromstring(resp.text, parser=uft8_parser))
        item.origin = data
        item.title = (
            data.find("h2.title").text()
            if data.find("h2.title")
            else data.find("h1.title").text()
        )
        item.type = data.find('#tags a[href^="/category/"] .name').text()
        item.date = data.find("#tags time").attr("datetime")
        item.tags = [
            i.text()
            for i in data.find('#tags a:not([href*="/search/?q=pages"]) .name').items()
        ]


async def nhentai_title_search(title: str) -> List[str]:
    query = preprocess_search_query(title)
    url = "https://nhentai.net/search/"
    params = {"q": query}
    async with AsyncClient(
        headers=NHENTAI_HEADERS, cookies=NHENTAI_COOKIES, proxies=config.proxy
    ) as session:
        resp = await session.get(url, params=params)
        if res := NHentaiResponse(resp.text, str(resp.url)):
            return await search_result_filter(res)

        return ["NHentai 暂时无法使用"]


async def search_result_filter(res: NHentaiResponse) -> List[str]:
    url = await shorten_url(res.url)
    if not res.raw:
        return [f"NHentai 搜索结果为空\n搜索页面：{url}"]

    for i in res.raw:
        await update_nhentai_info(i)

    # 优先找汉化版；没找到就优先找原版
    if chinese_res := [
        i for i in res.raw if "translated" in i.tags and "chinese" in i.tags
    ]:
        selected_res = chinese_res[0]
    elif not_translated_res := [i for i in res.raw if "translated" not in i.tags]:
        selected_res = not_translated_res[0]
    else:
        selected_res = res.raw[0]

    thumbnail = await handle_img(selected_res.thumbnail)
    date = arrow.get(selected_res.date).to("Asia/Shanghai").format("YYYY-MM-DD HH:mm")
    res_list = [
        "NHentai 搜索结果",
        thumbnail,
        selected_res.title,
        f"类型：{selected_res.type}",
        f"日期：{date}",
        f"来源：{selected_res.url}",
        f"搜索页面：{url}",
    ]
    return ["\n".join(res_list)]
