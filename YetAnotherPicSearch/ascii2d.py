from PicImageSearch import AsyncAscii2D, NetWork
from PicImageSearch.Utils import Ascii2DResponse

from .utils import handle_img, shorten_url


async def ascii2d_search(url: str, proxy: str, hide_img: bool) -> list[str]:
    async with NetWork(proxy=proxy) as client:
        ascii2d_color = AsyncAscii2D(client=client)
        ascii2d_bovw = AsyncAscii2D(bovw=True, client=client)
        color_res = await ascii2d_color.search(url)
        bovw_res = await ascii2d_bovw.search(url)

        async def get_final_res(res: Ascii2DResponse) -> str:
            if not res.raw[0].url:
                res.raw[0] = res.raw[1]
            thumbnail = await handle_img(res.raw[0].thumbnail, proxy, hide_img)
            res_list = [
                f"{thumbnail}",
                f"{res.raw[0].title}" if res.raw[0].title else "",
                f"Author：{res.raw[0].authors}" if res.raw[0].authors else "",
                f"{await shorten_url(res.raw[0].url)}" if res.raw[0].url else "",
            ]
            return "\n".join([i for i in res_list if i != ""])

        color_final_res = await get_final_res(color_res)
        bovw_final_res = await get_final_res(bovw_res)
        if color_final_res == bovw_final_res:
            return [f"Ascii2D 色合検索与特徴検索結果完全一致\n{color_final_res}"]

        return [
            f"Ascii2D 色合検索結果\n{color_final_res}",
            f"Ascii2D 特徴検索結果\n{bovw_final_res}",
        ]
