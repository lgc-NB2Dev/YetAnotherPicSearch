from typing import Annotated

from cookit.pyd import field_validator
from nonebot import get_plugin_config
from pydantic import BaseModel, Field, HttpUrl


class ConfigModel(BaseModel):
    nickname: set[str]

    proxy: str | None = None

    saucenao_api_key: str
    ascii2d_base_url: Annotated[str, HttpUrl] = "https://ascii2d.net"
    hide_ascii2d_base_url: bool = True
    exhentai_cookies: str | None = None
    nhentai_useragent: str | None = None
    nhentai_cookies: str | None = None
    nhentai_base_url: Annotated[str, HttpUrl] = "https://nhentai.net"
    hide_nhentai_base_url: bool = True

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
    to_confuse_urls: list[str] = [
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

    @field_validator("ascii2d_base_url", mode="after")
    def ascii2d_base_url_validator(cls, v: str) -> str:  # noqa: N805
        return v.rstrip("/")

    @field_validator("proxy", mode="before")
    def proxy_validator(cls, v: str | None) -> str | None:  # noqa: N805
        if isinstance(v, str) and v.startswith("socks://"):
            raise ValueError(
                '请修改代理地址为 "socks5://" 或 "socks4://" 的格式，具体取决于你的代理协议！',
            )
        return v


config = get_plugin_config(ConfigModel)
