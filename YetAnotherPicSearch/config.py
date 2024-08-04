from typing import List, Optional, Set

from cookit.pyd import field_validator
from nonebot import get_plugin_config
from pydantic import BaseModel, Field


class ConfigModel(BaseModel):
    nickname: Set[str]

    proxy: Optional[str] = None

    saucenao_api_key: str
    exhentai_cookies: Optional[str] = None
    nhentai_useragent: Optional[str] = None
    nhentai_cookies: Optional[str] = None

    saucenao_low_acc: int = 60
    auto_use_ascii2d: bool = True

    search_keyword: str = "搜图"
    search_keyword_only: bool = False
    search_in_group_only_keyword: bool = True
    search_immediately: bool = True
    wait_for_image_timeout: int = 180

    hide_img: bool = False
    hide_img_when_low_acc: bool = True
    hide_img_when_whatanime_r18: bool = True
    saucenao_nsfw_hide_level: int = Field(2, ge=0, le=3)
    forward_search_result: bool = True
    to_confuse_urls: List[str] = [
        "ascii2d.net",
        "danbooru.donmai.us",
        "konachan.com",
        "pixiv.net",
        "saucenao.com",
        "yandex.com",
    ]

    cache_expire: int = 3

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
