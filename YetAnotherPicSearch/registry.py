from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from typing import Optional, TypeAlias, TypeVar

from httpx import AsyncClient
from nonebot_plugin_alconna.uniseg import UniMessage

SearchFunctionReturnTuple: TypeAlias = tuple[
    list[UniMessage],
    Optional["SearchFunctionType"],
]
SearchFunctionReturnType: TypeAlias = list[UniMessage] | SearchFunctionReturnTuple
SearchFunctionType: TypeAlias = Callable[
    [bytes, AsyncClient, str],
    Awaitable[SearchFunctionReturnType],
]

TSF = TypeVar("TSF", bound=SearchFunctionType)


@dataclass
class SearchFunctionInfo:
    func: SearchFunctionType


registered_search_func: dict[str, SearchFunctionInfo] = {}


def search_function(*modes: str) -> Callable[[TSF], TSF]:
    def deco(func: TSF) -> TSF:
        info = SearchFunctionInfo(func)
        for mode in modes:
            registered_search_func[mode] = info
        return func

    return deco
