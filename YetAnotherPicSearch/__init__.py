import asyncio
import re
from collections import defaultdict
from typing import Any, DefaultDict, Dict, List, Optional, Tuple, Union

import arrow
from nonebot.adapters.onebot.v11 import (
    ActionFailed,
    Bot,
    GroupMessageEvent,
    Message,
    MessageEvent,
    PrivateMessageEvent,
)
from nonebot.matcher import Matcher
from nonebot.params import CommandArg
from nonebot.plugin.on import on_command, on_message
from nonebot.rule import Rule
from tinydb import JSONStorage, Query, TinyDB
from tinydb.middlewares import CachingMiddleware

from .ascii2d import ascii2d_search
from .cache import clear_expired_cache, exist_in_cache
from .config import config
from .ehentai import ehentai_search
from .iqdb import iqdb_search
from .result import Result
from .saucenao import saucenao_search

sending_lock: DefaultDict[Tuple[Union[int, str], str], asyncio.Lock] = defaultdict(
    asyncio.Lock
)


def has_images(event: MessageEvent) -> bool:
    message = event.reply.message if event.reply else event.message
    return bool([i for i in message if i.type == "image"])


async def to_me_with_images(bot: Bot, event: MessageEvent) -> bool:
    at_me = bool(
        [i for i in event.message if i.type == "at" and i.data["qq"] == bot.self_id]
    )
    has_image = has_images(event)
    if isinstance(event, PrivateMessageEvent):
        return has_image and config.search_immediately
    # 群里回复机器人发送的消息时，必须带上 "再搜"才会搜图，否则会被无视
    if event.reply and event.reply.sender.user_id == int(bot.self_id):
        return (
            has_image
            and (event.to_me or at_me)
            and "再搜" in event.message.extract_plain_text()
        )
    return has_image and (event.to_me or at_me)


IMAGE_SEARCH = on_message(rule=Rule(to_me_with_images), priority=5)
IMAGE_SEARCH_MODE = on_command("搜图", priority=5)


@IMAGE_SEARCH_MODE.handle()
async def handle_first_receive(matcher: Matcher, args: Message = CommandArg()) -> None:
    mode, purge = get_args(args)
    matcher.state["ARGS"] = (mode, purge)
    if [i for i in args if i.type == "image"]:
        matcher.set_arg("IMAGES", args)


async def image_search(
    url: str,
    mode: str,
    purge: bool,
    db: TinyDB,
    proxy: Optional[str] = config.proxy,
    hide_img: bool = config.hide_img,
) -> List[str]:
    image_md5 = re.search("[A-F0-9]{32}", url)[0]  # type: ignore
    _result = exist_in_cache(db, image_md5, mode)
    cached = bool(_result)
    if purge or not _result:
        result_dict: Dict[str, Any] = {}
        try:
            if mode == "a2d":
                result_dict["ascii2d"] = await ascii2d_search(url, proxy, hide_img)
            elif mode == "iqdb":
                result_dict["iqdb"] = await iqdb_search(url, proxy, hide_img)
            elif mode == "ex":
                result_dict["ex"] = await ehentai_search(url, proxy, hide_img)
            else:
                result_dict["saucenao"] = await saucenao_search(
                    url, mode, proxy, hide_img
                )
        except Exception as e:
            thumbnail = await handle_img(url, proxy, False)
            return [f"{thumbnail}\n❌️ 该图搜图失败，请稍后再试\nE: {repr(e)}"]
        result_dict["mode"] = mode
        result_dict["image_md5"] = image_md5
        result_dict["update_at"] = arrow.now().for_json()
        _result = Result(result_dict)
        db.upsert(
            _result.__dict__, (Query().image_md5 == image_md5) & (Query().mode == mode)
        )
    if mode == "a2d":
        final_res = _result.ascii2d
    elif mode == "iqdb":
        final_res = _result.iqdb
    elif mode == "ex":
        final_res = _result.ex
    else:
        final_res = _result.saucenao
    if cached and not purge:
        return [f"[缓存] {i}" for i in final_res]
    return final_res


def get_image_urls(event: MessageEvent) -> List[str]:
    message = event.reply.message if event.reply else event.message
    return [i.data["url"] for i in message if i.type == "image" and i.data.get("url")]


def get_args(msg: Message) -> Tuple[str, bool]:
    mode = "all"
    plain_text = msg.extract_plain_text()
    args = ["pixiv", "danbooru", "doujin", "anime", "a2d", "ex", "iqdb"]
    if plain_text:
        for i in args:
            if f"--{i}" in plain_text:
                mode = i
                break
    purge = "--purge" in plain_text
    return mode, purge


async def send_result_message(
    bot: Bot, event: MessageEvent, msg_list: List[str]
) -> None:
    if isinstance(event, PrivateMessageEvent):
        for msg in msg_list:
            start_time = arrow.now()
            async with sending_lock[(event.user_id, "private")]:
                await bot.send_private_msg(user_id=event.user_id, message=msg)
                await asyncio.sleep(
                    max(1 - (arrow.now() - start_time).total_seconds(), 0)
                )
    elif isinstance(event, GroupMessageEvent):
        flag = config.group_forward_search_result and len(msg_list) > 1
        if flag:
            try:
                start_time = arrow.now()
                async with sending_lock[(event.group_id, "group")]:
                    await send_group_forward_msg(bot, event, msg_list)
                    await asyncio.sleep(
                        max(1 - (arrow.now() - start_time).total_seconds(), 0)
                    )
            except ActionFailed:
                flag = False
        if not flag:
            for msg in msg_list:
                start_time = arrow.now()
                async with sending_lock[(event.group_id, "group")]:
                    await bot.send_group_msg(group_id=event.group_id, message=msg)
                    await asyncio.sleep(
                        max(1 - (arrow.now() - start_time).total_seconds(), 0)
                    )


async def send_group_forward_msg(
    bot: Bot, event: GroupMessageEvent, msg_list: List[str]
) -> None:
    await bot.send_group_forward_msg(
        group_id=event.group_id,
        messages=[
            {
                "type": "node",
                "data": {
                    "name": "\u200b",
                    "uin": bot.self_id,
                    "content": msg,
                },
            }
            for msg in msg_list
        ],
    )


@IMAGE_SEARCH.handle()
@IMAGE_SEARCH_MODE.got("IMAGES", prompt="请发送图片")
async def handle_image_search(bot: Bot, event: MessageEvent, matcher: Matcher) -> None:
    image_urls = get_image_urls(event)
    if not image_urls:
        await IMAGE_SEARCH_MODE.reject()
    if "ARGS" in matcher.state:
        mode, purge = matcher.state["ARGS"]
    else:
        mode, purge = get_args(event.message)
    db = TinyDB(
        "cache.json",
        storage=CachingMiddleware(JSONStorage),  # type: ignore
        encoding="utf-8",
        sort_keys=True,
        indent=4,
        ensure_ascii=False,
    )
    search_results = await asyncio.gather(
        *[image_search(i, mode, purge, db) for i in image_urls]
    )
    for i in search_results:
        await send_result_message(bot, event, i)
    clear_expired_cache(db)
    db.close()
