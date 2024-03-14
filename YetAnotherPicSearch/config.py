from typing import List, Literal, Optional, Set

from nonebot import get_plugin_config
from nonebot.compat import PYDANTIC_V2
from pydantic import BaseModel

if PYDANTIC_V2:
    from pydantic import field_validator  # type: ignore

else:
    from pydantic import validator

    def field_validator(
        __field: str,
        *fields: str,
        mode: Literal["before", "after", "wrap", "plain"] = "after",
    ):
        return validator(__field, *fields, pre=(mode == "before"), allow_reuse=True)


class Config(BaseModel):
    superusers: Set[str]
    nickname: Set[str]

    # 触发搜图的关键词
    search_keyword: str = "搜图"
    # 只响应含有搜图关键词的消息 (优先级高于 search_immediately)
    search_keyword_only: bool = False
    # 私聊发送图片立即搜图，否则需要先发送搜图关键词
    search_immediately: bool = True
    # 隐藏所有搜索结果的缩略图
    hide_img: bool = False
    # saucenao / iqdb 得到低相似度结果时隐藏结果缩略图
    hide_img_when_low_acc: bool = False
    # whatanime 得到 R18 结果时隐藏结果缩略图
    hide_img_when_whatanime_r18: bool = False
    # 对 saucenao 的搜索结果进行 NSFW 判断的严格程度 (依次递增) , 启用后自动隐藏相应的 NSFW 结果的缩略图
    # 0 表示不判断， 1 只判断明确的， 2 包括可疑的， 3 非明确为 SFW 的
    saucenao_nsfw_hide_level: int = 0
    # saucenao 相似度低于这个百分比将被认定为相似度过低
    saucenao_low_acc: int = 60
    # 是否在 saucenao 或 iqdb 相似度过低时 / ehentai 无结果时 自动使用 ascii2d
    auto_use_ascii2d: bool = True
    # 若结果消息有多条，采用合并转发方式发送搜图结果
    forward_search_result: bool = True
    # 大部分请求所使用的代理: http / socks4(a) / socks5(h)
    proxy: Optional[str] = None
    # saucenao 搜图结果缓存过期时间 (天)
    cache_expire: int = 3
    # saucenao APIKEY，必填，否则无法使用 saucenao 搜图
    saucenao_api_key: str
    # exhentai cookies，选填，没有的情况下自动改用 e-hentai 搜图
    exhentai_cookies: Optional[str] = None
    # 用来绕过 nhentai cloudflare 拦截的 useragent
    nhentai_useragent: Optional[str] = None
    # 用来绕过 nhentai cloudflare 拦截的 cookie
    nhentai_cookies: Optional[str] = None
    # 要处理的红链网址列表
    to_confuse_urls: List[str] = [
        "ascii2d.net",
        "danbooru.donmai.us",
        "konachan.com",
        "pixiv.net",
    ]

    @field_validator("saucenao_api_key", mode="before")
    def saucenao_api_key_validator(cls, v: str) -> str:
        if not v:
            raise ValueError("请配置 saucenao_api_key 否则无法正常使用搜图功能！")
        return v

    @field_validator("proxy", mode="before")
    def proxy_validator(cls, v: Optional[str]) -> Optional[str]:
        if isinstance(v, str) and v.startswith("socks://"):
            raise ValueError('请修改代理地址为 "socks5://" 或 "socks4://" 的格式，具体取决于你的代理协议！')
        return v


config = get_plugin_config(Config)
