import arrow
from nonebot import on_regex
from nonebot.adapters.onebot.v11 import (
    Bot,
    GroupMessageEvent,
    Message,
    MessageEvent,
    PrivateMessageEvent,
)
from nonebot.rule import to_me
from tinydb import JSONStorage, TinyDB
from tinydb.middlewares import CachingMiddleware

from .ascii2d import ascii2d_search
from .cache import clear_expired_cache, exist_in_cache, get_imagehash_by_url
from .config import config
from .saucenao import saucenao_search

if config.proxy:
    PROXY = config.proxy
else:
    PROXY = None

IMAGE_SEARCH = on_regex(pattern=r"\[CQ:image.+?]", rule=to_me(), priority=5)


async def image_search(
    url: str, mode: str, purge: bool, proxy: str, hide_img: bool = config.hide_img
) -> str:
    db = TinyDB(
        "cache.json",
        storage=CachingMiddleware(JSONStorage),
        encoding="utf-8",
        sort_keys=True,
        indent=4,
        ensure_ascii=False,
    )
    image_hash = await get_imagehash_by_url(url, proxy)
    result = await exist_in_cache(db, image_hash, mode)
    if purge or not result:
        result = {}
        final_res = ""
        if mode == "a2d":
            result["ascii2d"] = await ascii2d_search(url, proxy, hide_img)
        else:
            result["saucenao"] = await saucenao_search(url, mode, proxy, hide_img)
        result["mode"] = mode
        result["image_hash"] = image_hash
        result["update_at"] = arrow.now().for_json()
        db.insert(result)
    else:
        final_res = "[缓存]"
    await clear_expired_cache(db)
    db.close()
    if mode == "a2d":
        final_res += result["ascii2d"]
    else:
        final_res += result["saucenao"]
    return final_res


async def get_image_urls_with_args(args: Message) -> (list[str], str, bool):
    image_urls = []
    for i in args:
        if i.type == "image":
            image_urls.append(i.data["url"])
    mode = "all"
    plain_text = args.extract_plain_text()
    args = ["a2d", "pixiv", "danbooru", "doujin", "anime"]
    if plain_text:
        for i in args:
            if f"--{i}" in plain_text:
                mode = i
    purge = "--purge" in plain_text
    return image_urls, mode, purge


@IMAGE_SEARCH.handle()
async def handle_image_search(bot: Bot, event: MessageEvent):
    image_urls, mode, purge = await get_image_urls_with_args(event.message)
    for i in image_urls:
        msgs = await image_search(i, mode, purge, PROXY)
        msg_list = msgs.split("\n\n")
        if isinstance(event, PrivateMessageEvent):
            for msg in msg_list:
                await bot.send_private_msg(user_id=event.user_id, message=msg)
        elif isinstance(event, GroupMessageEvent):
            if config.group_forward_search_result and len(msg_list) > 1:
                await bot.send_group_forward_msg(
                    group_id=event.group_id,
                    messages=[
                        {
                            "type": "node",
                            "data": {
                                "name": event.sender.nickname,
                                "uin": event.user_id,
                                "content": msg,
                            },
                        }
                        for msg in msg_list
                    ],
                )
            else:
                for msg in msg_list:
                    await bot.send_group_msg(group_id=event.group_id, message=msg)
