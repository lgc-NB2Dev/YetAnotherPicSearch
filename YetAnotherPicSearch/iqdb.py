from typing import List, Optional

from PicImageSearch import Iqdb, Network

from .utils import get_source, handle_img, shorten_url


async def iqdb_search(url: str, proxy: Optional[str], hide_img: bool) -> List[str]:
    async with Network(proxies=proxy) as client:
        iqdb = Iqdb(client=client)
        res = await iqdb.search(url)
        if not res or not res.raw:
            return ["Iqdb 暂时无法使用"]
        selected_res = res.raw[0]
        # 优先取 danbooru 或 yande.re
        danbooru_res_list = [i for i in res.raw if i.source == "Danbooru"]
        yandere_res_list = [i for i in res.raw if i.source == "yande.re"]
        if danbooru_res_list:
            selected_res = danbooru_res_list[0]
        elif yandere_res_list:
            selected_res = yandere_res_list[0]
        thumbnail = await handle_img(selected_res.thumbnail, proxy, hide_img)
        source = (
            await shorten_url(await get_source(selected_res.url, proxy))
            if selected_res.url
            else ""
        )
        res_list = [
            f"Iqdb（{selected_res.similarity}%）",
            thumbnail,
            selected_res.url or "",
            f"来源：{source}" if source else "",
        ]
        return ["\n".join([i for i in res_list if i != ""])]
