from typing import List

from httpx import AsyncClient
from PicImageSearch import BaiDu

from .utils import async_lock, handle_img, shorten_url


@async_lock()
async def baidu_search(url: str, client: AsyncClient) -> List[str]:
    baidu = BaiDu(client=client)
    res = await baidu.search(url)
    _url = await shorten_url(res.url)
    if not res.raw:
        return [f"Baidu 搜索结果为空\n搜索页面：{_url}"]
    thumbnail = await handle_img(res.raw[0].thumbnail)
    res_list = [
        "Baidu 搜索结果",
        thumbnail,
        res.raw[0].url,
        f"搜索页面：{_url}",
    ]
    return ["\n".join([i for i in res_list if i])]
