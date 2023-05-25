from typing import List

from httpx import AsyncClient
from PicImageSearch import Yandex
from PicImageSearch.model import YandexResponse

from .utils import async_lock, handle_img


@async_lock()
async def yandex_search(file: bytes, client: AsyncClient) -> List[str]:
    yandex = Yandex(client=client)
    if res := await yandex.search(file=file):
        return await search_result_filter(res)
    return ["Yandex 暂时无法使用"]


async def search_result_filter(
    res: YandexResponse,
) -> List[str]:
    if not res.raw:
        return [f"Yandex 搜索结果为空\n搜索页面：{res.url}"]

    thumbnail = await handle_img(res.raw[0].thumbnail)
    res_list = [
        "Yandex 搜索结果",
        thumbnail,
        res.raw[0].size,
        res.raw[0].title,
        res.raw[0].source,
        res.raw[0].content,
        f"来源：{res.raw[0].url}",
        f"搜索页面：{res.url}",
    ]
    return ["\n".join([i for i in res_list if i])]
