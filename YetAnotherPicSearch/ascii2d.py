from typing import List

from aiohttp import ClientSession
from PicImageSearch import Ascii2D
from PicImageSearch.model import Ascii2DResponse

from .config import config
from .utils import DEFAULT_HEADERS, get_image_bytes_by_url, handle_img, shorten_url


async def ascii2d_search(url: str, client: ClientSession, hide_img: bool) -> List[str]:
    ascii2d_color = Ascii2D(client=client)
    color_res = await ascii2d_color.search(url)
    if not color_res.raw:
        # 当 url 搜索抽风时，自动改用 file 搜索
        file = await get_image_bytes_by_url(url)
        color_res = await ascii2d_color.search(file=file)
        if not color_res.raw:
            return ["Ascii2D 暂时无法使用"]
    # 针对 QQ 图片链接反盗链做处理
    if color_res.raw[0].hash == "5bb9bec07e71ef10a1a47521d396811d":
        url = f"https://images.weserv.nl/?url={url}"
        color_res = await ascii2d_color.search(url)
    async with ClientSession(headers=DEFAULT_HEADERS) as session:
        resp = await session.get(
            color_res.url.replace("/color/", "/bovw/"), proxy=config.proxy
        )
        bovw_res = Ascii2DResponse(await resp.text(), str(resp.url))

    async def get_final_res(res: Ascii2DResponse) -> List[str]:
        selected_res = [i for i in res.raw if i.title or i.url][0]
        thumbnail = await handle_img(selected_res.thumbnail, hide_img)
        _url = await shorten_url(selected_res.url) if selected_res.url else ""
        author = selected_res.author
        if author and selected_res.author_url:
            author_url = await shorten_url(selected_res.author_url)
            author = f"[{author}]({author_url})"
        res_list = [
            thumbnail,
            selected_res.title,
            selected_res.detail,
            f"作者：{author}" if author else "",
            f"来源：{_url}" if _url else "",
            f"搜索页面：{res.url}",
        ]
        return [i for i in res_list if i]

    color_final_res = await get_final_res(color_res)
    bovw_final_res = await get_final_res(bovw_res)
    if color_final_res[1:-1] == bovw_final_res[1:-1]:
        return ["Ascii2D 色合検索与特徴検索結果完全一致\n" + "\n".join(color_final_res)]

    return [
        f"Ascii2D 色合検索結果\n" + "\n".join(color_final_res),
        f"Ascii2D 特徴検索結果\n" + "\n".join(bovw_final_res),
    ]
