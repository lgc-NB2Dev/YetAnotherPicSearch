from httpx import AsyncClient
from nonebot_plugin_alconna.uniseg import UniMessage
from PicImageSearch import Iqdb

from ..config import config
from ..registry import SearchFunctionReturnType, search_function
from ..utils import (
    async_lock,
    combine_message,
    get_source,
    get_valid_url,
    handle_img,
    shorten_url,
)
from .ascii2d import ascii2d_search


@search_function("iqdb")
@async_lock()
async def iqdb_search(
    file: bytes,
    client: AsyncClient,
    _: str,
) -> SearchFunctionReturnType:
    iqdb = Iqdb(client=client)
    res = await iqdb.search(file=file)
    if not res.raw:
        return (
            [UniMessage.text("Iqdb 暂时无法使用，自动使用 Ascii2D 进行搜索")],
            ascii2d_search,
        )

    final_res: list[UniMessage] = []
    # 如果遇到搜索结果相似度低的情况，去除第一个只有提示信息的空结果
    low_acc = False
    if res.raw[0].content == "No relevant matches":
        low_acc = True
        res.raw.pop(0)
    selected_res = res.raw[0]
    hide_img = config.hide_img or (low_acc and config.hide_img_when_low_acc)

    # 优先取 danbooru 或 yande.re
    danbooru_res_list = [i for i in res.raw if i.source == "Danbooru"]
    yandere_res_list = [i for i in res.raw if i.source == "yande.re"]
    if danbooru_res_list:
        selected_res = danbooru_res_list[0]
    elif yandere_res_list:
        selected_res = yandere_res_list[0]

    thumbnail = await handle_img(selected_res.thumbnail, hide_img)
    source = await get_source(selected_res.url)
    if source:
        if get_valid_url(source):
            source = await shorten_url(source)
        source = f"来源：{source}"
    res_list = [
        f"Iqdb ({selected_res.similarity}%)",
        thumbnail,
        await shorten_url(selected_res.url),
        source,
        f"搜索页面：{res.url}",
    ]
    final_res.append(combine_message(res_list))

    if low_acc and config.auto_use_ascii2d:
        final_res.append(
            UniMessage.text(
                f"相似度 {selected_res.similarity}% 过低，自动使用 Ascii2D 进行搜索",
            ),
        )
        return final_res, ascii2d_search

    return final_res
