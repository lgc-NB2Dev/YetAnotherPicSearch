from typing import List

from aiohttp import ClientSession
from PicImageSearch import BaiDu

from .utils import handle_img, shorten_url


async def baidu_search(url: str, client: ClientSession, hide_img: bool) -> List[str]:
    baidu = BaiDu(client=client)
    res = await baidu.search(url)
    _url = await shorten_url(res.url)
    if not res.raw:
        return [f"Baidu 搜索结果为空\n搜索页面：{_url}"]
    thumbnail = await handle_img(res.raw[0].thumbnail, hide_img)
    res_list = [
        f"Baidu ({res.raw[0].similarity}%)",
        thumbnail,
        res.raw[0].title,
        res.raw[0].url,
        f"搜索页面：{_url}",
    ]
    return ["\n".join([i for i in res_list if i])]
