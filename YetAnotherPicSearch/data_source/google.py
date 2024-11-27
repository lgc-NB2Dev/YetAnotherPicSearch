import base64

from httpx import AsyncClient
from nonebot_plugin_alconna.uniseg import Segment, UniMessage
from PicImageSearch import Google
from PicImageSearch.model import GoogleResponse

from ..registry import SearchFunctionReturnType, search_function
from ..utils import async_lock, combine_message, shorten_url


@search_function("google")
@async_lock()
async def google_search(
    file: bytes,
    client: AsyncClient,
    _: str,
) -> SearchFunctionReturnType:
    google = Google(client=client)
    if res := await google.search(file=file):
        return await search_result_filter(res)
    return [UniMessage.text("Google 暂时无法使用")]


async def search_result_filter(res: GoogleResponse) -> list[UniMessage[Segment]]:
    url = await shorten_url(res.url)
    if not res.raw:
        return [UniMessage.text(f"Google 搜索结果为空\n搜索页面：{url}")]

    selected_res = next((i for i in res.raw if i.thumbnail), res.raw[0])
    if not selected_res.thumbnail:
        return [UniMessage.text(f"Google 搜索结果为空\n搜索页面：{url}")]

    thumbnail = UniMessage.image(
        raw=base64.b64decode(selected_res.thumbnail.split(",", 1)[1]),
    )
    res_list = [
        "Google 搜索结果",
        thumbnail,
        selected_res.title,
        f"来源：{selected_res.url}",
        f"搜索页面：{url}",
    ]
    return [combine_message(res_list)]
