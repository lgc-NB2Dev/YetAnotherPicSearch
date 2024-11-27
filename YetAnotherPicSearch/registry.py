from collections.abc import Awaitable
from dataclasses import dataclass
from typing import Callable, Optional, TypeVar, Union

from httpx import AsyncClient
from nonebot_plugin_alconna.uniseg import UniMessage
from typing_extensions import TypeAlias

SearchFunctionReturnTuple: TypeAlias = tuple[
    list[UniMessage],
    Optional["SearchFunctionType"],
]
SearchFunctionReturnType: TypeAlias = Union[list[UniMessage], SearchFunctionReturnTuple]
SearchFunctionType: TypeAlias = Callable[
    [bytes, AsyncClient, str],
    Awaitable[SearchFunctionReturnType],
]

TSF = TypeVar("TSF", bound=SearchFunctionType)


@dataclass
class SearchFunctionInfo:
    func: SearchFunctionType


registered_search_func: dict[str, SearchFunctionInfo] = {}


def search_function(*modes: str):
    def deco(func: TSF) -> TSF:
        info = SearchFunctionInfo(func)
        for mode in modes:
            registered_search_func[mode] = info
        return func

    return deco
