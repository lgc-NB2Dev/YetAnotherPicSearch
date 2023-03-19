import re
from asyncio import sleep
from typing import List, Optional, Tuple

from aiohttp import ClientSession
from PicImageSearch import SauceNAO
from PicImageSearch.model import SauceNAOItem, SauceNAOResponse
from yarl import URL

from .ascii2d import ascii2d_search
from .config import config
from .ehentai import ehentai_title_search
from .nhentai import nhentai_title_search
from .utils import SEARCH_FUNCTION_TYPE, get_source, handle_img, shorten_url
from .whatanime import whatanime_search

SAUCENAO_DB = {
    "all": 999,
    "pixiv": 5,
    "danbooru": 9,
    "anime": [21, 22],
    "doujin": [18, 38],
    "fakku": 16,
}


async def saucenao_search(
    url: str, client: ClientSession, mode: str
) -> Tuple[List[str], Optional[SEARCH_FUNCTION_TYPE]]:
    db = SAUCENAO_DB[mode]
    if isinstance(db, list):
        saucenao = SauceNAO(
            client=client,
            api_key=config.saucenao_api_key,
            hide=config.saucenao_nsfw_hide_level,
            dbs=db,
        )
    else:
        saucenao = SauceNAO(
            client=client,
            api_key=config.saucenao_api_key,
            hide=config.saucenao_nsfw_hide_level,
            db=db,
        )
    res = await saucenao.search(url)

    if (
        res
        and res.status == 429
        and "4 searches every 30 seconds" in res.origin["header"]["message"]
    ):
        await sleep(30 / 4)
        return await saucenao_search(url, client, mode)

    if not res or not res.raw:
        final_res = ["SauceNAO 暂时无法使用，自动使用 Ascii2D 进行搜索"]
        return final_res, ascii2d_search

    selected_res = get_best_result(res, res.raw[0])
    return await get_final_res(mode, res, selected_res)


def get_best_pixiv_result(
    res: SauceNAOResponse, selected_res: SauceNAOItem
) -> SauceNAOItem:
    pixiv_res_list = list(
        filter(
            lambda x: x.index_id == SAUCENAO_DB["pixiv"]
            and x.url
            and abs(x.similarity - selected_res.similarity) < 5,
            res.raw,
        )
    )
    if len(pixiv_res_list) > 1:
        selected_res = min(
            pixiv_res_list,
            key=lambda x: int(re.search(r"\d+", x.url).group()),  # type: ignore
        )
    return selected_res


def get_best_result(res: SauceNAOResponse, selected_res: SauceNAOItem) -> SauceNAOItem:
    # 如果结果为 pixiv ，尝试找到原始投稿，避免返回盗图者的投稿
    if selected_res.index_id == SAUCENAO_DB["pixiv"]:
        selected_res = get_best_pixiv_result(res, selected_res)
    # 如果地址有多个，优先取 danbooru
    elif len(selected_res.ext_urls) > 1:
        for i in selected_res.ext_urls:
            if "danbooru" in i:
                selected_res.url = i
    return selected_res


async def get_final_res(
    mode: str, res: SauceNAOResponse, selected_res: SauceNAOItem
) -> Tuple[List[str], Optional[SEARCH_FUNCTION_TYPE]]:
    low_acc = selected_res.similarity < config.saucenao_low_acc
    hide_img = config.hide_img or (
        selected_res.hidden or low_acc and config.hide_img_when_low_acc
    )

    thumbnail = await handle_img(selected_res.thumbnail, hide_img)

    url = await shorten_url(selected_res.url)
    source = selected_res.source if selected_res.source != selected_res.title else ""
    if not source and selected_res.url:
        source = await get_source(selected_res.url)
    if source and URL(source).host:
        source = await shorten_url(source)

    author_link = (
        f"[{selected_res.author}]({await shorten_url(selected_res.author_url)})"
        if selected_res.author and selected_res.author_url
        else ""
    )

    res_list = [
        f"SauceNAO ({selected_res.similarity}%)",
        thumbnail,
        selected_res.title,
        f"作者：{author_link}" if author_link else "",
        url if url != source else "",
        f"来源：{source}" if source else "",
        f"搜索页面：{res.url}",
    ]

    final_res = []

    if res.long_remaining < 10:
        final_res.append(f"SauceNAO 24h 内仅剩 {res.long_remaining} 次使用次数")

    final_res.append("\n".join([i for i in res_list if i]))

    if low_acc:
        extra_res, extra_handle = await handle_saucenao_low_acc(mode, selected_res)
        final_res.extend(extra_res)
        return final_res, extra_handle
    elif selected_res.index_id in SAUCENAO_DB["doujin"]:  # type: ignore
        title = selected_res.title.replace("-", "")
        final_res.extend(await search_on_ehentai_and_nhentai(title))
    # 如果搜索结果为 fakku ，额外返回 ehentai 的搜索结果
    elif selected_res.index_id == SAUCENAO_DB["fakku"]:
        title = f"{selected_res.author} {selected_res.title}"
        final_res.extend(await search_on_ehentai_and_nhentai(title))
    elif selected_res.index_id in SAUCENAO_DB["anime"]:  # type: ignore
        return final_res, whatanime_search

    return final_res, None


async def search_on_ehentai_and_nhentai(title: str) -> List[str]:
    title_search_result = await ehentai_title_search(title)

    if (
        title_search_result[0].startswith("EHentai 搜索结果为空")
        and config.nhentai_useragent
        and config.nhentai_cookies
    ):
        title_search_result.append("自动使用 NHentai 进行搜索")
        title_search_result.extend(await nhentai_title_search(title))

    return title_search_result


async def handle_saucenao_low_acc(
    mode: str, selected_res: SauceNAOItem
) -> Tuple[List[str], Optional[SEARCH_FUNCTION_TYPE]]:
    final_res: List[str] = []
    # 因为 saucenao 的动画搜索数据库更新不够快，所以当搜索模式为动画时额外增加 whatanime 的搜索结果
    if mode == "anime":
        return final_res, whatanime_search
    elif config.auto_use_ascii2d:
        final_res.append(f"相似度 {selected_res.similarity}% 过低，自动使用 Ascii2D 进行搜索")
        return final_res, ascii2d_search

    return final_res, None
