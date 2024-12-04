from typing import TYPE_CHECKING

from nonebot_plugin_alconna.uniseg import UniMessage
from PicImageSearch import Yandex

from ..registry import SearchFunctionReturnType, search_function
from ..utils import async_lock, combine_message, handle_img, shorten_url

if TYPE_CHECKING:
    from httpx import AsyncClient
    from PicImageSearch.model import YandexResponse


@search_function("yandex")
@async_lock()
async def yandex_search(
    file: bytes,
    client: "AsyncClient",
    _: str,
) -> SearchFunctionReturnType:
    yandex = Yandex(client=client)
    if res := await yandex.search(file=file):
        return await search_result_filter(res)
    return [UniMessage.text("Yandex 暂时无法使用")]


async def search_result_filter(res: "YandexResponse") -> list[UniMessage]:
    url = await shorten_url(res.url)
    if not res.raw:
        return [UniMessage.text(f"Yandex 搜索结果为空\n搜索页面：{url}")]

    thumbnail = await handle_img(res.raw[0].thumbnail)
    res_list = [
        "Yandex 搜索结果",
        thumbnail,
        res.raw[0].size,
        res.raw[0].title,
        res.raw[0].source,
        res.raw[0].content,
        f"来源：{res.raw[0].url}",
        f"搜索页面：{url}",
    ]
    return [combine_message(res_list)]
