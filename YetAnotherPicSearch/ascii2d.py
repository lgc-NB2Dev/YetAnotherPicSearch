from typing import List, Optional

from PicImageSearch import Ascii2D, Network
from PicImageSearch.model import Ascii2DResponse

from .utils import handle_img, shorten_url


async def ascii2d_search(url: str, proxy: Optional[str], hide_img: bool) -> List[str]:
    async with Network(proxies=proxy) as client:
        ascii2d_color = Ascii2D(client=client)
        ascii2d_bovw = Ascii2D(bovw=True, client=client)
        color_res = await ascii2d_color.search(url)
        bovw_res = await ascii2d_bovw.search(url)

        async def get_final_res(res: Ascii2DResponse) -> str:
            if not res or not res.raw:
                return ""
            if not res.raw[0].url:
                res.raw[0] = res.raw[1]
            thumbnail = await handle_img(res.raw[0].thumbnail, proxy, hide_img)
            _url = shorten_url(res.raw[0].url) if res.raw[0] else ""
            res_list = [
                f"{thumbnail}",
                f"{res.raw[0].title}" if res.raw[0].title else "",
                f"Author：{res.raw[0].author}" if res.raw[0].author else "",
                _url,
            ]
            return "\n".join([i for i in res_list if i != ""])

        color_final_res = await get_final_res(color_res)
        bovw_final_res = await get_final_res(bovw_res)
        if color_final_res == bovw_final_res:
            if color_final_res == "":
                return ["Ascii2D 暂时无法使用"]
            return [f"Ascii2D 色合検索与特徴検索結果完全一致\n{color_final_res}"]

        return [
            f"Ascii2D 色合検索結果\n{color_final_res}",
            f"Ascii2D 特徴検索結果\n{bovw_final_res}",
        ]
