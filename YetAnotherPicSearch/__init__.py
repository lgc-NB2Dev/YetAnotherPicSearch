import asyncio
import re
from collections import defaultdict
from typing import DefaultDict, List, Optional, Tuple, Union

import aiohttp
import arrow
from diskcache import Cache
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

from .ascii2d import ascii2d_search
from .cache import exist_in_cache, upsert_cache
from .config import config
from .ehentai import ehentai_search
from .iqdb import iqdb_search
from .saucenao import saucenao_search
from .utils import handle_img

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
    _cache: Cache,
    proxy: Optional[str] = config.proxy,
    hide_img: bool = config.hide_img,
) -> List[str]:
    url = await get_universal_img_url(url)
    image_md5 = re.search("[A-F0-9]{32}", url)[0]  # type: ignore
    if not purge and (result := exist_in_cache(_cache, image_md5, mode)):
        return [f"[缓存] {i}" for i in result]
    try:
        if mode == "a2d":
            result = await ascii2d_search(url, proxy, hide_img)
        elif mode == "iqdb":
            result = await iqdb_search(url, proxy, hide_img)
        elif mode == "ex":
            result = await ehentai_search(url, proxy, hide_img)
        else:
            result = await saucenao_search(url, mode, proxy, hide_img)
    except Exception as e:
        thumbnail = await handle_img(url, proxy, False)
        return [f"{thumbnail}\n❌️ 该图搜图失败，请稍后再试\nE: {repr(e)}"]
    upsert_cache(_cache, image_md5, mode, result)
    return result


async def get_universal_img_url(url: str) -> str:
    fianl_url = url.replace(
        "/c2cpicdw.qpic.cn/offpic_new/", "/gchat.qpic.cn/gchatpic_new/"
    )
    final_url = re.sub(r"/\d+/+\d+-\d+-", "/0/0-0-", fianl_url)
    final_url = re.sub(r"\?.*$", "", final_url)
    async with aiohttp.ClientSession() as session:
        async with session.get(final_url) as resp:
            if resp.status == 200:
                return final_url
    return url


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
    if isinstance(event, GroupMessageEvent):
        current_sending_lock = sending_lock[(event.group_id, "group")]
    else:
        current_sending_lock = sending_lock[(event.user_id, "private")]
    if flag := (config.forward_search_result and len(msg_list) > 1):
        try:
            start_time = arrow.now()
            async with current_sending_lock:
                await send_forward_msg(bot, event, msg_list)
                await asyncio.sleep(
                    max(1 - (arrow.now() - start_time).total_seconds(), 0)
                )
        except ActionFailed:
            flag = False
    if not flag:
        for msg in msg_list:
            start_time = arrow.now()
            async with current_sending_lock:
                await send_msg(bot, event, msg)
                await asyncio.sleep(
                    max(1 - (arrow.now() - start_time).total_seconds(), 0)
                )


async def send_msg(bot: Bot, event: MessageEvent, message: str) -> None:
    await bot.send_msg(
        user_id=event.user_id if isinstance(event, PrivateMessageEvent) else 0,
        group_id=event.group_id if isinstance(event, GroupMessageEvent) else 0,
        message=message,
    )


async def send_forward_msg(bot: Bot, event: MessageEvent, msg_list: List[str]) -> None:
    await bot.send_forward_msg(
        user_id=event.user_id if isinstance(event, PrivateMessageEvent) else 0,
        group_id=event.group_id if isinstance(event, GroupMessageEvent) else 0,
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
    with Cache("picsearch_cache") as c:
        for i in image_urls:
            await send_result_message(bot, event, await image_search(i, mode, purge, c))
        c.expire()
