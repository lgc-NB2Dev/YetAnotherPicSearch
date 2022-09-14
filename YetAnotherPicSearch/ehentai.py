import itertools
from collections import defaultdict
from difflib import SequenceMatcher
from typing import Any, Dict, List

import arrow
from aiohttp import ClientSession
from PicImageSearch import EHentai
from PicImageSearch.model import EHentaiResponse

from .config import config
from .utils import DEFAULT_HEADERS, handle_img, shorten_url

EHENTAI_HEADERS = (
    {"Cookie": config.exhentai_cookies, **DEFAULT_HEADERS}
    if config.exhentai_cookies
    else DEFAULT_HEADERS
)


async def ehentai_search(url: str, client: ClientSession, hide_img: bool) -> List[str]:
    ex = bool(config.exhentai_cookies)
    ehentai = EHentai(client=client)
    if res := await ehentai.search(url, ex=ex):
        if not res.raw:
            # 如果第一次没找到，使搜索结果包含被删除的部分，并重新搜索
            async with ClientSession(headers=EHENTAI_HEADERS) as session:
                resp = await session.get(f"{res.url}&fs_exp=on", proxy=config.proxy)
                res = EHentaiResponse(await resp.text(), str(resp.url))
        return await search_result_filter(res, hide_img)
    return ["EHentai 暂时无法使用"]


async def ehentai_title_search(title: str, hide_img: bool) -> List[str]:
    url = "https://exhentai.org" if config.exhentai_cookies else "https://e-hentai.org"
    params: Dict[str, Any] = {"f_search": title}
    async with ClientSession(headers=EHENTAI_HEADERS) as session:
        resp = await session.get(url, proxy=config.proxy, params=params)
        if res := EHentaiResponse(await resp.text(), str(resp.url)):
            if not res.raw:
                # 如果第一次没找到，使搜索结果包含被删除的部分，并重新搜索
                params["advsearch"] = 1
                params["f_sname"] = "on"
                params["f_stags"] = "on"
                params["f_sh"] = "on"
                resp = await session.get(url, proxy=config.proxy, params=params)
                res = EHentaiResponse(await resp.text(), str(resp.url))
            # 只保留标题和搜索关键词相关度较高的结果，并排序，以此来提高准确度
            if res.raw:
                raw_with_ratio = [
                    (i, SequenceMatcher(lambda x: x == " ", title, i.title).ratio())
                    for i in res.raw
                ]
                raw_with_ratio.sort(key=lambda x: x[1], reverse=True)
                if filtered := [i[0] for i in raw_with_ratio if i[1] > 0.65]:
                    res.raw = filtered
                else:
                    res.raw = [i[0] for i in raw_with_ratio]
            return await search_result_filter(res, hide_img)
        return ["EHentai 暂时无法使用"]


async def search_result_filter(
    res: EHentaiResponse,
    hide_img: bool,
) -> List[str]:
    if not res.raw:
        _url = await shorten_url(res.url)
        return [f"EHentai 搜索结果为空\n搜索页面：{_url}"]
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
        group_list = list(group)
        if priority[key] > 0 and len(res.raw) != len(group_list):
            res.raw = [i for i in res.raw if i not in group_list]

    # 优先找汉化版或原版
    if chinese_res := [
        i for i in res.raw if all(tag in i.tags for tag in ["translated", "chinese"])
    ]:
        selected_res = chinese_res[0]
    elif not_translated_res := [i for i in res.raw if "translated" not in i.tags]:
        selected_res = not_translated_res[0]
    else:
        selected_res = res.raw[0]

    thumbnail = await handle_img(
        selected_res.thumbnail, hide_img, cookies=config.exhentai_cookies
    )
    date = arrow.get(selected_res.date).to("Asia/Shanghai").format("YYYY-MM-DD HH:mm")
    _url = await shorten_url(res.url)
    res_list = [
        "EHentai 搜索结果",
        thumbnail,
        selected_res.title,
        f"类型：{selected_res.type}",
        f"日期：{date}",
        f"来源：{selected_res.url}",
        f"搜索页面：{_url}",
    ]
    return ["\n".join([i for i in res_list if i])]
