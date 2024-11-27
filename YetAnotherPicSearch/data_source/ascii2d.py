import asyncio
import re
from typing import cast

from cookit import flatten
from cookit.loguru import logged_suppress
from httpx import AsyncClient, HTTPStatusError
from nonebot_plugin_alconna.uniseg import Segment, UniMessage
from PicImageSearch import Ascii2D
from PicImageSearch.model import Ascii2DResponse

from ..config import config
from ..registry import SearchFunctionReturnType, search_function
from ..utils import async_lock, combine_message, get_image_bytes_by_url, shorten_url


@search_function("a2d")
@async_lock()
async def ascii2d_search(
    file: bytes,
    client: AsyncClient,
    _: str,
) -> SearchFunctionReturnType:
    ascii2d_color = Ascii2D(base_url=config.ascii2d_base_url, client=client)
    color_res = await ascii2d_color.search(file=file)
    if not color_res.raw:
        return [UniMessage.text("Ascii2D 暂时无法使用")]

    resp_text, resp_url, _ = await ascii2d_color.get(
        re.sub(r"(/|%2F)color", r"\1bovw", color_res.url)
    )
    bovw_res = Ascii2DResponse(resp_text, resp_url)
    # 去除 bovw_res 中已经存在于 color_res 的部分
    color_res_origin_list = [str(i.origin) for i in color_res.raw]
    duplicated_raw = [
        i
        for i in bovw_res.raw
        if (str(i.origin) in color_res_origin_list and any(i.title or i.url_list))
    ]
    duplicated_count = len(duplicated_raw)
    bovw_res.raw = [i for i in bovw_res.raw if i not in duplicated_raw]

    res = await asyncio.gather(
        get_final_res(color_res),
        get_final_res(bovw_res, bovw=True, duplicated_count=duplicated_count),
    )
    return flatten(res)  # type: ignore


async def get_final_res(
    res: Ascii2DResponse, bovw: bool = False, duplicated_count: int = 0
) -> list[UniMessage[Segment]]:
    final_res_list: list[UniMessage[Segment]] = []
    for r in res.raw:
        if not (r.title or r.url_list):
            continue

        msg: UniMessage[Segment] = UniMessage()
        if config.hide_img:
            msg += f"预览图链接：{r.thumbnail}\n"
        else:
            thumbnail = None
            with logged_suppress("Failed to get image", HTTPStatusError):
                thumbnail = await get_image_bytes_by_url(r.thumbnail)
            if not thumbnail:
                continue
            msg += UniMessage.image(raw=thumbnail)
            msg += "\n"

        title = r.title
        if r.url_list and title == r.url_list[0].text:
            title = ""

        source = r.url or (cast(str, r.url_list[0].href) if r.url_list else "")
        source = await shorten_url(source) if source else ""

        author = r.author
        if author and r.author_url:
            author_url = await shorten_url(r.author_url)
            author = f"[{author}]({author_url})"

        res_list = [
            r.detail,
            title,
            f"作者：{author}" if author else "",
            f"来源：{source}" if source else "",
        ]
        msg += combine_message(res_list)

        final_res_list.append(msg)
        if len(final_res_list) == 3:
            break

    return [
        UniMessage.text(
            f"Ascii2D {'特徴' if bovw else '色合'}検索結果"
            + (
                f" (已去除与特徴検索結果重复的 {duplicated_count} 个结果)"
                if duplicated_count
                else ""
            )
            + f"\n搜索页面：{await shorten_url(res.url)}",
        ),
        *final_res_list,
    ]
