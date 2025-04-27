from typing import cast

import arrow
from httpx import AsyncClient
from lxml.html import HTMLParser, fromstring
from nonebot_plugin_alconna.uniseg import UniMessage
from pyquery import PyQuery

from ..config import config
from ..nhentai_model import NHentaiItem, NHentaiResponse
from ..utils import (
    combine_message,
    filter_results_with_ratio,
    handle_img,
    parse_cookies,
    preprocess_search_query,
    shorten_url,
)

NHENTAI_HEADERS = (
    {"User-Agent": config.nhentai_useragent} if config.nhentai_cookies and config.nhentai_useragent else None
)
NHENTAI_COOKIES = parse_cookies(config.nhentai_cookies)


def get_nh_display_base():
    return config.nhentai_base_url if config.hide_nhentai_base_url else "https://nhentai.net"


async def update_nhentai_info(item: NHentaiItem) -> None:
    async with AsyncClient(
        headers=NHENTAI_HEADERS,
        cookies=NHENTAI_COOKIES,
        proxy=config.proxy,
    ) as session:
        resp = await session.get(item.with_base_url(config.nhentai_base_url))
        uft8_parser = HTMLParser(encoding="utf-8")
        data = PyQuery(fromstring(resp.text, parser=uft8_parser))
        item.origin = data
        item.title = cast(
            "str",
            (data.find("h2.title").text() if data.find("h2.title") else data.find("h1.title").text()),
        )
        item.type = cast("str", data.find('#tags a[href^="/category/"] .name').text())
        item.date = cast("str", data.find("#tags time").attr("datetime"))
        item.tags = [cast("str", i.text()) for i in data.find('#tags a:not([href*="/search/?q=pages"]) .name').items()]


async def nhentai_title_search(title: str) -> list[UniMessage]:
    query = preprocess_search_query(title)
    async with AsyncClient(
        headers=NHENTAI_HEADERS,
        cookies=NHENTAI_COOKIES,
        proxy=config.proxy,
    ) as session:
        resp = await session.get(
            f"{config.nhentai_base_url}/search/",
            params={"q": query},
        )
        if res := NHentaiResponse(
            resp.text,
            str(resp.url).replace(f"{config.nhentai_base_url}/", "", 1),
        ):
            # 只保留标题和搜索关键词相关度较高的结果，并排序，以此来提高准确度
            if res.raw:
                res.raw = filter_results_with_ratio(res, title)
            return await search_result_filter(res)

        return [UniMessage.text("NHentai 暂时无法使用")]


async def search_result_filter(res: NHentaiResponse) -> list[UniMessage]:
    display_base = get_nh_display_base()
    url = await shorten_url(
        res.with_base_url(display_base),
        force_shorten=True,
    )
    if not res.raw:
        return [UniMessage.text(f"NHentai 搜索结果为空\n搜索页面：{url}")]

    for i in res.raw:
        await update_nhentai_info(i)

    # 优先找汉化版；没找到就优先找原版
    if chinese_res := [i for i in res.raw if "translated" in i.tags and "chinese" in i.tags]:
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
        f"来源：{selected_res.with_base_url(display_base)}",
        f"搜索页面：{url}",
    ]
    return [combine_message(res_list)]
