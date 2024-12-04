from typing import TYPE_CHECKING

from nonebot_plugin_alconna.uniseg import UniMessage
from PicImageSearch import BaiDu

from ..registry import SearchFunctionReturnType, search_function
from ..utils import async_lock, combine_message, handle_img, shorten_url

if TYPE_CHECKING:
    from httpx import AsyncClient


@search_function("baidu")
@async_lock()
async def baidu_search(
    file: bytes,
    client: "AsyncClient",
    _: str,
) -> SearchFunctionReturnType:
    baidu = BaiDu(client=client)
    res = await baidu.search(file=file)
    _url = await shorten_url(res.url)
    if not res.raw:
        return [UniMessage.text(f"Baidu 搜索结果为空\n搜索页面：{_url}")]
    thumbnail = await handle_img(res.raw[0].thumbnail)
    res_list = [
        "Baidu 搜索结果",
        thumbnail,
        res.raw[0].url,
        f"搜索页面：{_url}",
    ]
    return [combine_message(res_list)]
