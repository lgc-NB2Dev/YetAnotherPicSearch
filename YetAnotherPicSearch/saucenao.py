from PicImageSearch import AsyncSauceNAO, NetWork

from .ascii2d import ascii2d_search
from .config import config
from .utils import get_source, handle_img, shorten_pixiv_url


async def saucenao_search(url: str, mode: str, proxy: str, hide_img: bool) -> list[str]:
    saucenao_db = {"all": 999, "pixiv": 5, "danbooru": 9, "anime": 21, "doujin": 18}
    async with NetWork(proxy=proxy) as client:
        saucenao = AsyncSauceNAO(
            client=client, api_key=config.saucenao_api_key, db=saucenao_db[mode]
        )
        res = await saucenao.search(url)
        final_res = []
        if res is not None:
            thumbnail = await handle_img(res.raw[0].thumbnail, proxy, hide_img)
            source = await shorten_pixiv_url(await get_source(res.raw[0].url, proxy))
            res_list = [
                f"SauceNAO（{res.raw[0].similarity}%）",
                f"{thumbnail}",
                f"{res.raw[0].origin['data'].get('jp_name')}"
                if mode == "doujin"
                else f"{res.raw[0].title}",
                f"Author：{res.raw[0].author}" if res.raw[0].author else "",
                f"{await shorten_pixiv_url(res.raw[0].url)}",
                f"Source：{source}" if source else "",
            ]
            final_res.append("\n".join([i for i in res_list if i != ""]))
            if (
                config.use_ascii2d_when_low_acc
                and res.raw[0].similarity < config.saucenao_low_acc
            ):
                final_res.append(f"相似度 {res.raw[0].similarity}% 过低，自动使用 Ascii2D 进行搜索")
                final_res.extend(await ascii2d_search(url, proxy, hide_img))
        else:
            final_res.append("SauceNAO 暂时无法使用，自动使用 Ascii2D 进行搜索")
            final_res.extend(await ascii2d_search(url, proxy, hide_img))
        return final_res
