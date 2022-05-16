from typing import Any, Dict, List, Optional, Union

import aiohttp
from lxml.html import HTMLParser, fromstring
from PicImageSearch import EHentai, Network
from PicImageSearch.model import EHentaiItem, EHentaiResponse
from pyquery import PyQuery

from .config import config
from .utils import handle_img


class EHentaiResponseAioHttp:
    def __init__(self, resp_text: str, resp_url: str):
        self.origin: str = resp_text
        utf8_parser = HTMLParser(encoding="utf-8")
        data = PyQuery(fromstring(self.origin, parser=utf8_parser))
        self.raw: List[EHentaiItem] = [
            EHentaiItem(i) for i in data.find(".glcat").parents("tr").items()
        ]
        self.url: str = resp_url


async def ehentai_search(url: str, proxy: Optional[str], hide_img: bool) -> List[str]:
    async with Network(proxies=proxy, cookies=config.exhentai_cookies) as client:
        ex = bool(config.exhentai_cookies)
        ehentai = EHentai(client=client)
        if res := await ehentai.search(url, ex=ex):
            if not res.raw:
                # 如果第一次没找到，使搜索结果包含被删除的部分，并重新搜索
                ehentai = EHentai(client=client, exp=True)
                res = await ehentai.search(url, ex=ex)
            return await search_result_filter(res, proxy, hide_img)
        return ["EHentai 暂时无法使用"]


async def ehentai_title_search(
    title: str, proxy: Optional[str], hide_img: bool
) -> List[str]:
    headers = {}
    if cookies := config.exhentai_cookies:
        headers["Cookie"] = cookies
    url = "https://exhentai.org" if cookies else "https://e-hentai.org"
    params: Dict[str, Any] = {"f_search": title}
    async with aiohttp.ClientSession(headers=headers) as session:
        resp = await session.get(url, proxy=proxy, params=params)
        if res := EHentaiResponseAioHttp(await resp.text(), str(resp.url)):
            if not res.raw:
                # 如果第一次没找到，使搜索结果包含被删除的部分，并重新搜索
                params["advsearch"] = 1
                params["f_sname"] = "on"
                params["f_stags"] = "on"
                params["f_sh"] = "on"
                resp = await session.get(url, proxy=proxy, params=params)
                res = EHentaiResponseAioHttp(await resp.text(), str(resp.url))
            return await search_result_filter(res, proxy, hide_img)
        return ["EHentai 暂时无法使用"]


async def search_result_filter(
    res: Union[EHentaiResponse, EHentaiResponseAioHttp],
    proxy: Optional[str],
    hide_img: bool,
) -> List[str]:
    if not res.raw:
        return ["EHentai 搜索结果为空"]
        # 尽可能过滤掉图集，除非只有图集
    if non_image_set_list := [i for i in res.raw if i.type != "Image Set"]:
        res.raw = non_image_set_list
    selected_res = res.raw[0]
    # 优先找汉化版
    for i in res.raw:
        if "translated" in i.tags and "chinese" in i.tags:
            selected_res = i
            break
    thumbnail = await handle_img(
        selected_res.thumbnail, proxy, hide_img, config.exhentai_cookies
    )
    res_list = [
        "EHentai 搜索结果",
        thumbnail,
        selected_res.title,
        f"类型：{selected_res.type}",
        f"日期：{selected_res.date}",
        f"来源：{selected_res.url}",
        "-" * 20,
        f"搜索页面：{res.url}",
    ]
    return ["\n".join([i for i in res_list if i != ""])]
