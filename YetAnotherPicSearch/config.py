from typing import List, Optional, Set

from cookit.pyd import field_validator
from nonebot import get_plugin_config
from pydantic import BaseModel


class ConfigModel(BaseModel):
    nickname: Set[str]

    # saucenao APIKEY，必填
    saucenao_api_key: str

    # 大部分请求所使用的代理: http / socks4(a) / socks5(h)
    proxy: Optional[str] = None
    # 触发搜图的关键词
    search_keyword: str = "搜图"
    # 只响应含有搜图关键词开头的消息 (优先级高于 search_in_group_only_keyword 与 search_immediately)
    search_keyword_only: bool = False
    # 是否在群聊中只响应搜图关键词开头的消息
    search_in_group_only_keyword: bool = True
    # 私聊发送图片立即搜图，否则需要先以搜图关键词开头
    search_immediately: bool = True
    # 当用户未提供图片是，提示用户提供图片的等待时间（秒）
    wait_for_image_timeout: int = 180
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
    # saucenao 搜图结果缓存过期时间 (天)
    cache_expire: int = 3
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
        "saucenao.com",
        "yandex.com",
    ]

    @field_validator("saucenao_api_key", mode="before")
    def saucenao_api_key_validator(cls, v: str) -> str:  # noqa: N805
        if not v:
            raise ValueError("请配置 SAUCENAO_API_KEY 否则无法正常使用搜图功能！")
        return v

    @field_validator("proxy", mode="before")
    def proxy_validator(cls, v: Optional[str]) -> Optional[str]:  # noqa: N805
        if isinstance(v, str) and v.startswith("socks://"):
            raise ValueError(
                '请修改代理地址为 "socks5://" 或 "socks4://" 的格式，具体取决于你的代理协议！',
            )
        return v


config = get_plugin_config(ConfigModel)
