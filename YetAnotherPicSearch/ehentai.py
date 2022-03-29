from typing import List, Optional

from PicImageSearch import EHentai, Network

from .config import config
from .utils import handle_img


async def ehentai_search(url: str, proxy: Optional[str], hide_img: bool) -> List[str]:
    async with Network(proxies=proxy, cookies=config.exhentai_cookies) as client:
        ex = bool(config.exhentai_cookies)
        ehentai = EHentai(client=client)
        res = await ehentai.search(url, ex=ex)
        if res:
            if not res.raw:
                # 如果第一次没找到，使搜索结果包含被删除的部分，并重新搜索
                ehentai = EHentai(client=client, exp=True)
                res = await ehentai.search(url, ex=ex)
            if not res.raw:
                return ["EHentai 搜索结果为空"]
            selected_res = res.raw[0]
            # 尽可能过滤掉图集，除非只有图集
            non_image_set_list = [i for i in res.raw if i.type != "Image Set"]
            if non_image_set_list:
                res.raw = non_image_set_list
            # 优先找汉化版
            for i in res.raw:
                if "translated" in i.tags and "chinese" in i.tags:
                    selected_res = i
            thumbnail = await handle_img(
                selected_res.thumbnail, proxy, hide_img, config.exhentai_cookies
            )
            res_list = [
                "EHentai 搜索结果",
                f"搜索页面：{res.url}",
                thumbnail,
                selected_res.title,
                f"类型：{selected_res.type}" if selected_res.type else "",
                f"日期：{selected_res.date}" if selected_res.date else "",
                f"来源：{selected_res.url}" if selected_res.url else "",
            ]
            return ["\n".join([i for i in res_list if i != ""])]
        return ["EHentai 暂时无法使用"]
