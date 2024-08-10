import math
from typing import Any, Dict

from httpx import AsyncClient
from nonebot_plugin_alconna.uniseg import UniMessage
from PicImageSearch import TraceMoe

from ..config import config
from ..registry import SearchFunctionReturnType
from ..utils import async_lock, combine_message, handle_img


@async_lock()
async def whatanime_search(
    file: bytes,
    client: AsyncClient,
    _: str,
) -> SearchFunctionReturnType:
    whatanime = TraceMoe(client=client)
    res = await whatanime.search(file=file)
    if res and res.raw:
        time = res.raw[0].From
        minutes = math.floor(time / 60)
        seconds = math.floor(time % 60)
        time_str = f"{minutes:02d}:{seconds:02d}"

        if res.raw[0].isAdult:
            thumbnail = await handle_img(
                res.raw[0].cover_image,
                config.hide_img or config.hide_img_when_whatanime_r18,
            )
        else:
            thumbnail = await handle_img(
                res.raw[0].cover_image,
            )

        chinese_title = res.raw[0].title_chinese
        native_title = res.raw[0].title_native

        start_date = date_to_str(res.raw[0].start_date)
        end_date = ""
        if (end_date_year := res.raw[0].end_date["year"]) and end_date_year > 0:
            end_date = date_to_str(res.raw[0].end_date)
        episode = res.raw[0].episode or 1
        res_list = [
            f"WhatAnime ({res.raw[0].similarity}%)",
            f"该截图出自第 {episode} 集的 {time_str}",
            thumbnail,
            native_title,
            chinese_title if chinese_title != native_title else "",
            f"类型：{res.raw[0].type}-{res.raw[0].format}",
            f"开播：{start_date}",
            f"完结：{end_date}" if end_date else "",
        ]
        return [combine_message(res_list)]

    return [UniMessage.text("WhatAnime 暂时无法使用")]


def date_to_str(date: Dict[str, Any]) -> str:
    return f"{date['year']}-{date['month']}-{date['day']}"
