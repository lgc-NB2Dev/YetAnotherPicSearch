from nonebot import get_driver
from pydantic import BaseSettings


class Config(BaseSettings):

    hide_img: bool = False  # 隐藏所有搜索结果的缩略图
    saucenao_low_acc: int = 60  # saucenao 相似度低于这个百分比将被认定为相似度过低
    use_ascii2d_when_low_acc: bool = True  # 是否在 saucenao 相似度过低时自动使用 ascii2d
    group_forward_search_result: bool = True  # 若结果消息有多条，采用合并转发方式发送搜图结果（私聊不生效）
    proxy: str = ""  # 大部分请求所使用的代理，支持 http(s):// 和 socks://
    cache_expire: int = 7  # 搜图结果缓存过期时间（天）
    saucenao_api_key: str = ""  # saucenao APIKEY，必填，否则无法使用 saucenao 搜图

    class Config:
        extra = "ignore"


global_config = get_driver().config
config = Config(**global_config.dict())
