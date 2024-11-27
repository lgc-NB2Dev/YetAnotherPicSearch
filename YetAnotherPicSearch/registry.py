from collections.abc import Awaitable
from dataclasses import dataclass
from typing import Callable, Optional, TypeVar, Union

from httpx import AsyncClient
from nonebot_plugin_alconna.uniseg import Segment, UniMessage
from typing_extensions import TypeAlias

SearchFunctionReturnTuple: TypeAlias = tuple[
    list[UniMessage[Segment]],
    Optional["SearchFunctionType"],
]
SearchFunctionReturnType: TypeAlias = Union[
    list[UniMessage[Segment]], SearchFunctionReturnTuple
]
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
