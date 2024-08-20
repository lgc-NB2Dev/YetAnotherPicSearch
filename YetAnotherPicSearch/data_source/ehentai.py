import itertools
import re
from collections import defaultdict
from typing import Any, Dict, List, cast

import arrow
from httpx import AsyncClient
from nonebot_plugin_alconna.uniseg import UniMessage
from PicImageSearch import EHentai
from PicImageSearch.model import EHentaiResponse
from pyquery import PyQuery

from ..config import config
from ..registry import SearchFunctionReturnType, search_function
from ..utils import (
    DEFAULT_HEADERS,
    async_lock,
    combine_message,
    filter_results_with_ratio,
    handle_img,
    parse_cookies,
    preprocess_search_query,
    shorten_url,
)
from .ascii2d import ascii2d_search


@search_function("ex")
@async_lock(freq=8)
async def ehentai_search(
    file: bytes,
    client: AsyncClient,
    mode: str,
) -> SearchFunctionReturnType:
    ex = bool(config.exhentai_cookies)
    ehentai = EHentai(client=client)

    if not (res := await ehentai.search(file=file, ex=ex)):
        if "Please wait a bit longer between each file search" in res.origin:
            return await ehentai_search(file, client, mode)
    else:
        final_res = await search_result_filter(res)
        if not res.raw and config.auto_use_ascii2d:
            final_res.append(UniMessage.text("自动使用 Ascii2D 进行搜索"))
            return final_res, ascii2d_search
        return final_res

    return [UniMessage.text("EHentai 暂时无法使用")]


async def ehentai_title_search(title: str) -> List[UniMessage]:
    query = preprocess_search_query(title)
    url = "https://exhentai.org" if config.exhentai_cookies else "https://e-hentai.org"
    params: Dict[str, Any] = {"f_search": query}

    async with AsyncClient(
        headers=DEFAULT_HEADERS,
        cookies=parse_cookies(config.exhentai_cookies),
        proxies=config.proxy,
    ) as session:
        resp = await session.get(url, params=params)
        if res := EHentaiResponse(resp.text, str(resp.url)):
            if not res.raw:
                # 如果第一次没找到，使搜索结果包含被删除的部分，并重新搜索
                params["advsearch"] = 1
                params["f_sname"] = "on"
                params["f_sh"] = "on"
                resp = await session.get(url, params=params)
                res = EHentaiResponse(resp.text, str(resp.url))

            # 只保留标题和搜索关键词相关度较高的结果，并排序，以此来提高准确度
            if res.raw:
                res.raw = filter_results_with_ratio(res, title)
            return await search_result_filter(res)

        return [UniMessage.text("EHentai 暂时无法使用")]


async def search_result_filter(
    res: EHentaiResponse,
) -> List[UniMessage]:
    url = await shorten_url(res.url)
    if not res.raw:
        return [UniMessage.text(f"EHentai 搜索结果为空\n搜索页面：{url}")]

    # 尝试过滤已删除的
    if not_expunged_res := [
        i for i in res.raw if not PyQuery(i.origin)("[id^='posted'] s")
    ]:
        res.raw = not_expunged_res

    # 尝试过滤无主题的杂图图集
    if not_themeless_res := [i for i in res.raw if "themeless" not in " ".join(i.tags)]:
        res.raw = not_themeless_res

    # 尝试过滤评分低于 3 星的
    if above_3_star_res := [
        i
        for i in res.raw
        if get_star_rating(cast(str, PyQuery(i.origin)("div.ir").attr("style"))) >= 3
    ]:
        res.raw = above_3_star_res

    # 尽可能过滤掉非预期结果(大概
    priority = defaultdict(lambda: 0)
    priority["Image Set"] = 1
    priority["Non-H"] = 2
    priority["Western"] = 3
    priority["Misc"] = 4
    priority["Cosplay"] = 5
    priority["Asian Porn"] = 6
    res.raw.sort(key=lambda x: priority[x.type], reverse=True)
    for key, group in itertools.groupby(res.raw, key=lambda x: x.type):  # type: ignore
        if priority[key] > 0:
            group_list = list(group)
            if len(res.raw) != len(group_list):
                res.raw = [i for i in res.raw if i not in group_list]

    # 优先找汉化版；没找到就优先找原版
    if chinese_res := [
        i
        for i in res.raw
        if "translated" in " ".join(i.tags) and "chinese" in " ".join(i.tags)
    ]:
        selected_res = chinese_res[0]
    elif not_translated_res := [
        i for i in res.raw if "translated" not in " ".join(i.tags)
    ]:
        selected_res = not_translated_res[0]
    else:
        selected_res = res.raw[0]

    thumbnail = await handle_img(
        selected_res.thumbnail,
        cookies=config.exhentai_cookies,
    )
    date = arrow.get(selected_res.date).to("Asia/Shanghai").format("YYYY-MM-DD HH:mm")
    favorited = bool(selected_res.origin.find("[id^='posted']").eq(0).attr("style"))
    res_list = [
        "EHentai 搜索结果",
        thumbnail,
        selected_res.title,
        ("❤️ 已收藏" if favorited else ""),
        f"类型：{selected_res.type}",
        f"日期：{date}",
        f"来源：{selected_res.url}",
        f"搜索页面：{url}",
    ]
    return [combine_message(res_list)]


def get_star_rating(css_style: str) -> float:
    x, y = re.search(r"(-?\d+)px (-\d+)px", css_style).groups()  # type: ignore
    star_rating = 5 - int(x.rstrip("px")) / -16
    if y == "-21px":
        star_rating -= 0.5
    return star_rating
