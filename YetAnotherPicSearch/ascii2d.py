from PicImageSearch import AsyncAscii2D, NetWork

from .utils import handle_img


async def ascii2d_search(url: str, proxy: str, hide_img: bool) -> str:
    async with NetWork(proxy=proxy) as client:
        ascii2d_color = AsyncAscii2D(client=client)
        ascii2d_bovw = AsyncAscii2D(bovw=True, client=client)
        color_res = await ascii2d_color.search(url)
        bovw_res = await ascii2d_bovw.search(url)
        if not any(
            [color_res.raw[0].title, color_res.raw[0].authors, color_res.raw[0].url]
        ):
            color_res.raw[0] = color_res.raw[1]
        if not any(
            [bovw_res.raw[0].title, bovw_res.raw[0].authors, bovw_res.raw[0].url]
        ):
            bovw_res.raw[0] = bovw_res.raw[1]
        res_list = [
            f"Ascii2D 色合検索\n",
            f"{await handle_img(color_res.raw[0].thumbnail, proxy, hide_img)}\n",
            f"{color_res.raw[0].title}\n",
            f"Author：{color_res.raw[0].authors}\n",
            f"{color_res.raw[0].url}",
            "\n\n",
            f"Ascii2D 特徴検索\n",
            f"{await handle_img(bovw_res.raw[0].thumbnail, proxy, hide_img)}\n",
            f"{bovw_res.raw[0].title}\n",
            f"Author：{bovw_res.raw[0].authors}\n",
            f"{bovw_res.raw[0].url}",
        ]
        final_res = ""
        for i in res_list:
            if i not in ["\n", "Author：\n"]:
                final_res += i
        return final_res
