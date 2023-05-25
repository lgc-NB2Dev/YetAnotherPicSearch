from typing import List

from httpx import AsyncClient
from PicImageSearch import Google
from PicImageSearch.model import GoogleResponse

from .utils import async_lock, get_image_bytes_by_url, shorten_url


@async_lock()
async def google_search(url: str, client: AsyncClient) -> List[str]:
    google = Google(client=client)
    _file = await get_image_bytes_by_url(url)
    if res := await google.search(file=_file):
        return await search_result_filter(res)
    return ["Google 暂时无法使用"]


async def search_result_filter(
    res: GoogleResponse,
) -> List[str]:
    url = await shorten_url(res.url)
    if not res.raw:
        return [f"Google 搜索结果为空\n搜索页面：{url}"]

    selected_res = next((i for i in res.raw if i.thumbnail), res.raw[0])
    if not selected_res.thumbnail:
        return [f"Google 搜索结果为空\n搜索页面：{url}"]

    thumbnail = f"[CQ:image,file=base64://{selected_res.thumbnail.split(',', 1)[1]}]"
    res_list = [
        "Google 搜索结果",
        thumbnail,
        selected_res.title,
        f"来源：{selected_res.url}",
        f"搜索页面：{url}",
    ]
    return ["\n".join([i for i in res_list if i])]
