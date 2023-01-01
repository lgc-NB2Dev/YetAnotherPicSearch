from typing import List

from aiohttp import ClientSession
from PicImageSearch import Iqdb
from yarl import URL

from .ascii2d import ascii2d_search
from .config import config
from .utils import get_source, handle_img, shorten_url


async def iqdb_search(url: str, client: ClientSession, hide_img: bool) -> List[str]:
    iqdb = Iqdb(client=client)
    res = await iqdb.search(url)
    if not res.raw:
        return ["Iqdb 暂时无法使用"]
    final_res: List[str] = []
    # 如果遇到搜索结果相似度低的情况，去除第一个只有提示信息的空结果
    low_acc = False
    if res.raw[0].content == "No relevant matches":
        low_acc = True
        res.raw.pop(0)
    selected_res = res.raw[0]
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
        if URL(source).host:
            source = await shorten_url(source)
        source = f"来源：{source}"
    res_list = [
        f"Iqdb ({selected_res.similarity}%)",
        thumbnail,
        await shorten_url(selected_res.url),
        source,
        f"搜索页面：{res.url}",
    ]
    final_res.append("\n".join([i for i in res_list if i]))

    if low_acc and config.auto_use_ascii2d:
        final_res.append(f"相似度 {selected_res.similarity}% 过低，自动使用 Ascii2D 进行搜索")
        final_res.extend(await ascii2d_search(url, client, hide_img))

    return final_res
