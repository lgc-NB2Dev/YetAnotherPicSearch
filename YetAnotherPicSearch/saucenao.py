import re
from asyncio import sleep
from typing import List

from aiohttp import ClientSession
from PicImageSearch import SauceNAO
from yarl import URL

from .ascii2d import ascii2d_search
from .config import config
from .ehentai import ehentai_title_search
from .utils import get_source, handle_img, shorten_url
from .whatanime import whatanime_search


async def saucenao_search(
    url: str, mode: str, client: ClientSession, hide_img: bool
) -> List[str]:
    saucenao_db = {
        "all": 999,
        "pixiv": 5,
        "danbooru": 9,
        "anime": [21, 22],
        "doujin": [18, 38],
        "fakku": 16,
    }
    if isinstance(db := saucenao_db[mode], list):
        saucenao = SauceNAO(
            client=client,
            api_key=config.saucenao_api_key,
            hide=config.saucenao_nsfw_hide_level,
            dbs=db,
        )
    else:
        saucenao = SauceNAO(
            client=client,
            api_key=config.saucenao_api_key,
            hide=config.saucenao_nsfw_hide_level,
            db=db,
        )
    res = await saucenao.search(url)
    final_res = []
    if res and res.raw:
        selected_res = res.raw[0]
        # 如果结果为 pixiv ，尝试找到原始投稿，避免返回盗图者的投稿
        if selected_res.index_id == saucenao_db["pixiv"]:
            pixiv_res_list = list(
                filter(
                    lambda x: x.index_id == saucenao_db["pixiv"]
                    and x.url
                    and abs(x.similarity - selected_res.similarity) < 5,
                    res.raw,
                )
            )
            if len(pixiv_res_list) > 1:
                selected_res = min(
                    pixiv_res_list,
                    key=lambda x: int(re.search(r"\d+", x.url).group()),  # type: ignore
                )
        # 如果地址有多个，优先取 danbooru
        elif len(selected_res.ext_urls) > 1:
            for i in selected_res.ext_urls:
                if "danbooru" in i:
                    selected_res.url = i
        _hide_img = hide_img or selected_res.hidden
        if selected_res.similarity < config.saucenao_low_acc:
            _hide_img = _hide_img or config.hide_img_when_low_acc
        thumbnail = await handle_img(selected_res.thumbnail, _hide_img)
        source = selected_res.source
        if source and source == selected_res.title:
            source = ""
        if not source and selected_res.url:
            source = await get_source(selected_res.url)
        if source and URL(source).host:
            source = await shorten_url(source)
        _url = await shorten_url(selected_res.url)
        author = selected_res.author
        if author and selected_res.author_url:
            author = f"[{author}]({await shorten_url(selected_res.author_url)})"
        res_list = [
            f"SauceNAO ({selected_res.similarity}%)",
            thumbnail,
            selected_res.title,
            f"作者：{author}" if author else "",
            _url if _url != source else "",
            f"来源：{source}" if source else "",
            f"搜索页面：{res.url}",
        ]
        if res.long_remaining < 10:
            final_res.append(f"SauceNAO 24h 内仅剩 {res.long_remaining} 次使用次数")
        final_res.append("\n".join([i for i in res_list if i]))
        if selected_res.similarity < config.saucenao_low_acc:
            # 因为 saucenao 的动画搜索数据库更新不够快，所以当搜索模式为动画时额外增加 whatanime 的搜索结果
            if mode == "anime":
                final_res.extend(
                    await whatanime_search(
                        url, client, hide_img or config.hide_img_when_low_acc
                    )
                )
            elif config.auto_use_ascii2d:
                final_res.append(f"相似度 {selected_res.similarity}% 过低，自动使用 Ascii2D 进行搜索")
                final_res.extend(
                    await ascii2d_search(
                        url, client, hide_img or config.hide_img_when_low_acc
                    )
                )
        elif selected_res.index_id in saucenao_db["doujin"]:  # type: ignore
            final_res.extend(await ehentai_title_search(selected_res.title, hide_img))
        # 如果搜索结果为 fakku ，额外返回 ehentai 的搜索结果
        elif selected_res.index_id == saucenao_db["fakku"]:
            final_res.extend(
                await ehentai_title_search(
                    f"{selected_res.author} {selected_res.title}", hide_img
                )
            )
        elif selected_res.index_id in saucenao_db["anime"]:  # type: ignore
            final_res.extend(await whatanime_search(url, client, hide_img))
    elif (
        res
        and res.status == 429
        and "4 searches every 30 seconds" in res.origin["header"]["message"]
    ):
        await sleep(30 / 4)
        return await saucenao_search(url, mode, client, hide_img)
    else:
        final_res.append("SauceNAO 暂时无法使用，自动使用 Ascii2D 进行搜索")
        final_res.extend(await ascii2d_search(url, client, hide_img))
    return final_res
