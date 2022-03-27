import math
from typing import Any, Dict, List, Optional

from PicImageSearch import Network, TraceMoe

from .utils import handle_img


async def whatanime_search(url: str, proxy: Optional[str], hide_img: bool) -> List[str]:
    async with Network(proxies=proxy) as client:
        whatanime = TraceMoe(client=client)
        res = await whatanime.search(url=url)
        if res and res.raw:
            time = res.raw[0].From
            minutes = math.floor(time / 60)
            seconds = math.floor(time % 60)
            time_str = f"{minutes:02d}:{seconds:02d}"
            cover_image = await handle_img(
                res.raw[0].anime_info["coverImage"]["large"],
                proxy,
                hide_img,
            )
            chinese_title = res.raw[0].title_chinese
            native_title = res.raw[0].title_native
            _type = res.raw[0].anime_info["type"]
            _format = res.raw[0].anime_info["format"]

            def date_to_str(date: Dict[str, Any]) -> str:
                return f"{date['year']}-{date['month']}-{date['day']}"

            start_date = date_to_str(res.raw[0].anime_info["startDate"])
            end_date = ""
            if res.raw[0].anime_info["endDate"]["year"] > 0:
                end_date = date_to_str(res.raw[0].anime_info["endDate"])
            res_list = [
                f"WhatAnime（{res.raw[0].similarity}%）",
                f"该截图出自第 {res.raw[0].episode} 集的 {time_str}",
                cover_image,
                chinese_title,
                native_title,
                f"类型：{_type}-{_format}",
                f"开播：{start_date}",
                f"完结：{end_date}" if end_date else "",
            ]
            return ["\n".join([i for i in res_list if i != ""])]
        return ["WhatAnime 暂时无法使用"]
