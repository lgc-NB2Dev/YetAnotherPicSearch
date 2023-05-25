from typing import List

from httpx import AsyncClient
from PicImageSearch import Google
from PicImageSearch.model import GoogleResponse

from .utils import async_lock


@async_lock()
async def google_search(file: bytes, client: AsyncClient) -> List[str]:
    google = Google(client=client)
    if res := await google.search(file=file):
        return await search_result_filter(res)
    return ["Google 暂时无法使用"]


async def search_result_filter(
    res: GoogleResponse,
) -> List[str]:
    if not res.raw:
        return [f"Google 搜索结果为空\n搜索页面：{res.url}"]

    selected_res = next((i for i in res.raw if i.thumbnail), res.raw[0])
    if not selected_res.thumbnail:
        return [f"Google 搜索结果为空\n搜索页面：{res.url}"]

    thumbnail = f"[CQ:image,file=base64://{selected_res.thumbnail.split(',', 1)[1]}]"
    res_list = [
        "Google 搜索结果",
        thumbnail,
        selected_res.title,
        f"来源：{selected_res.url}",
        f"搜索页面：{res.url}",
    ]
    return ["\n".join([i for i in res_list if i])]
