# ruff: noqa: N999

import asyncio
from contextlib import asynccontextmanager, suppress
from dataclasses import dataclass
from pathlib import Path
from typing import List, Literal, NoReturn, Optional, Union, overload

from cookit.loguru import logged_suppress
from cookit.nonebot.alconna import RecallContext
from httpx import AsyncClient
from nonebot import logger, on_command, on_message
from nonebot.adapters import Bot as BaseBot, Event as BaseEvent, Message as BaseMessage
from nonebot.exception import ActionFailed, FinishedException
from nonebot.matcher import current_bot, current_event, current_matcher
from nonebot.params import _command, _command_arg
from nonebot.permission import SUPERUSER
from nonebot.typing import T_State
from nonebot_plugin_alconna.uniseg import (
    At,
    CustomNode,
    FallbackStrategy,
    Image,
    MsgTarget,
    Reference,
    Reply,
    SerializeFailed,
    Target,
    Text,
    UniMessage,
    UniMsg,
)
from nonebot_plugin_waiter import waiter
from PicImageSearch import Network

from .cache import msg_cache
from .config import config
from .registry import registered_search_func
from .utils import get_image_from_seg, post_image_process

KEY_IMAGES = "images"


@dataclass
class SearchArgs:
    mode: str = "all"
    purge: bool = False


async def extract_images(msg: UniMsg) -> List[Image]:
    if Reply in msg and isinstance((raw_reply := msg[Reply, 0].msg), BaseMessage):
        msg = await UniMessage.generate(message=raw_reply)
    return msg[Image]


async def rule_func_search_msg(
    bot: BaseBot,
    ev: BaseEvent,
    state: T_State,
    msg: UniMsg,
    target: MsgTarget,
) -> bool:
    if target.private:
        images = await extract_images(msg)
        state[KEY_IMAGES] = images
        return bool(images) and config.search_immediately

    # 指令检测在下方做了
    # 不太方便做是否回复 Bot 自己消息的判断，阉了吧
    return (not config.search_in_group_only_keyword) and (
        ev.is_tome()
        or any(True for x in msg if isinstance(x, At) and x.target == bot.self_id)
    )


async def extract_search_args() -> SearchArgs:
    ev = current_event.get()
    m = current_matcher.get()
    state = m.state

    args = SearchArgs()

    async def finish_with_unknown(arg: str) -> NoReturn:
        await m.finish(
            f"意外参数 {arg}\n使用指令 `{config.search_keyword} -h` 查看帮助",
        )

    async def parse_mode(arg: str):
        if arg.startswith("--") and (mode := arg[2:]) in registered_search_func:
            args.mode = mode
            return True
        return False

    async def is_purge(arg: str):
        if arg == "--purge":
            args.purge = True
            return True
        return False

    async def send_help(arg: str):
        if arg in ("-h", "--help"):
            await UniMessage.image(
                raw=(Path(__file__).parent / "res" / "usage.jpg").read_bytes(),
            ).finish(reply_to=True)
        return True

    msg = (
        _command_arg(state).extract_plain_text()
        if _command(state)
        else ev.get_plaintext()
    )
    for arg in msg.strip().lower().split():
        for func in (parse_mode, is_purge, send_help):
            if await func(arg):
                break
        else:
            await finish_with_unknown(arg)

    return args


async def get_images_from_ev(msg: UniMessage) -> List[Image]:
    m = current_matcher.get()
    state = m.state

    images = state.get(KEY_IMAGES) or await extract_images(msg)
    if images:
        return images

    @waiter(waits=["message"], keep_session=True)
    async def wait_msg(msg: UniMsg):
        return msg

    waited_msg = await wait_msg.wait(
        f"请在 {config.wait_for_image_timeout} 秒内发送你要搜索的图片，发送其他内容取消搜索",
    )
    if not waited_msg:
        await m.finish("操作超时，退出搜图")

    images = await extract_images(waited_msg)
    if not images:
        await m.finish("无效输入，退出搜图")

    return images


@asynccontextmanager
async def fail_with_msg(msg: Union[UniMessage, str], should_finish: bool = True):
    try:
        yield
    except Exception as e:
        logger.exception("Error occurred")
        asyncio.create_task(
            logger.catch(
                (msg if isinstance(msg, UniMessage) else UniMessage(msg)).send,
            )(reply_to=True),
        )
        if should_finish:
            raise FinishedException from e
    return


async def should_display_favorite(target: Target) -> bool:
    return (await SUPERUSER(current_bot.get(), current_event.get())) and target.private


async def send_msgs(
    msgs: List[UniMessage],
    target: Target,
    index: Optional[int] = None,
    display_fav: bool = False,
):
    def pre_process_msg(m: UniMessage):
        if index:
            m = UniMessage.text(f"第 {index} 张图片的搜索结果：\n") + m

        should_remove: List[str] = []
        if not display_fav:
            should_remove.append("❤️ 已收藏\n")
        for txt in should_remove:
            # alconna 的 text auto merge 害人
            # for seg in (x for x in m[Text] if (txt in x.text)):
            for seg in (x for x in m if isinstance(x, Text) and (txt in x.text)):
                seg.text = seg.text.replace(txt, "")

        return m

    msgs = [pre_process_msg(m) for m in msgs]
    msg_len = len(msgs)
    reply_to: Optional[str] = UniMessage.get_message_id()

    async def try_send():
        if config.forward_search_result and msg_len > 1:
            bot = current_bot.get()
            nodes = [
                CustomNode(
                    uid=bot.self_id,
                    name=(next(iter(config.nickname), None) or "YetAnotherPicSearch"),
                    content=x,
                )
                for x in msgs
            ]
            with suppress(SerializeFailed, ActionFailed):
                await UniMessage(Reference(nodes=nodes)).send(
                    target=target,
                    fallback=FallbackStrategy.forbid,
                    # reply_to=reply_to,
                )
                return

        for x in msgs:
            await x.send(
                target=target,
                fallback=FallbackStrategy.to_text,
                reply_to=reply_to,
            )

    with suppress(ActionFailed):
        await try_send()
        return

    target.private = True
    reply_to = None
    with suppress(ActionFailed):
        await try_send()
        return

    with logged_suppress("ActionFailed", ActionFailed):
        await UniMessage.text(
            "消息发送失败了呜呜喵，似乎是被某种神秘的力量拦截了喵",
        ).send(reply_to=True)


@overload
def make_cache_key(mode: str, seg: Image, raw: bytes) -> str: ...
@overload
def make_cache_key(
    mode: str,
    seg: Image,
    raw: Literal[None] = None,
) -> Optional[str]: ...
def make_cache_key(mode: str, seg: Image, raw: Optional[bytes] = None) -> Optional[str]:
    if seg.id:
        adapter_name = current_bot.get().adapter.get_name()
        base = f"id_{adapter_name}_{seg.id}"
    elif raw:
        base = f"hash_{hash(raw):x}"
    else:
        return None
    return f"{hash(f'{base}_{mode}'):x}"


async def handle_single_image(
    client: AsyncClient,
    seg: Image,
    mode: str,
    purge: bool,
    target: Target,
    index: Optional[int] = None,
    display_fav: bool = False,
):
    async def fetch_image(seg: Image) -> Optional[bytes]:
        async with fail_with_msg(
            f"图片{f' {index} ' if index else ''}下载失败",
            should_finish=False,
        ):
            return await get_image_from_seg(seg)
        return None

    # lazy fetch file if cache does not exist
    file = None
    cache_key = make_cache_key(mode, seg)
    if not cache_key:
        if not (file := await fetch_image(seg)):
            return
        cache_key = make_cache_key(mode, seg, file)

    if (not purge) and (cached_msgs := msg_cache.get(cache_key)):
        msgs = [(UniMessage.text("[缓存] ") + x) for x in cached_msgs]
        await send_msgs(msgs, target, index, display_fav)
        return

    # lazy fetch
    if (not file) and (not (file := await fetch_image(seg))):
        return
    file = post_image_process(file)

    messages: List[UniMessage] = []
    func = registered_search_func[mode].func
    while True:
        res = await func(file, client, mode)
        msgs, func = res if isinstance(res, tuple) else (res, None)
        messages.extend([x.copy() for x in msgs])
        await send_msgs(msgs, target, index, display_fav)
        if not func:
            break

    msg_cache[cache_key] = messages


async def search_handler(msg: UniMsg, target: MsgTarget):
    arg = await extract_search_args()
    images = await get_images_from_ev(msg)

    async with RecallContext() as recall:
        await recall.send("正在进行搜索，请稍候", reply_to=True)

        display_fav = await should_display_favorite(target)
        network = (
            Network(proxies=config.proxy, cookies=config.exhentai_cookies, timeout=60)
            if arg.mode == "ex"
            else Network(proxies=config.proxy)
        )
        multiple_images = len(images) > 1
        async with network as client:
            for index, seg in enumerate(images, 1):
                async with fail_with_msg(
                    f"第 {index} 张图搜索失败",
                    should_finish=False,
                ):
                    await handle_single_image(
                        client,
                        seg,
                        arg.mode,
                        arg.purge,
                        target,
                        index if multiple_images else None,
                        display_fav,
                    )


matcher_search_cmd = on_command(config.search_keyword, priority=1, block=True)
matcher_search_cmd.handle()(search_handler)
if not config.search_keyword_only:
    matcher_search_msg = on_message(rule=rule_func_search_msg, priority=2, block=True)
    matcher_search_msg.handle()(search_handler)
