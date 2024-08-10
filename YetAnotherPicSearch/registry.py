from dataclasses import dataclass
from typing import Awaitable, Callable, Dict, List, Optional, Tuple, TypeVar, Union
from typing_extensions import TypeAlias

from httpx import AsyncClient
from nonebot_plugin_alconna.uniseg import UniMessage

SearchFunctionReturnTuple: TypeAlias = Tuple[
    List[UniMessage],
    Optional["SearchFunctionType"],
]
SearchFunctionReturnType: TypeAlias = Union[List[UniMessage], SearchFunctionReturnTuple]
SearchFunctionType: TypeAlias = Callable[
    [bytes, AsyncClient, str],
    Awaitable[SearchFunctionReturnType],
]

TSF = TypeVar("TSF", bound=SearchFunctionType)


@dataclass
class SearchFunctionInfo:
    func: SearchFunctionType


registered_search_func: Dict[str, SearchFunctionInfo] = {}


def search_function(*modes: str):
    def deco(func: TSF) -> TSF:
        info = SearchFunctionInfo(func)
        for mode in modes:
            registered_search_func[mode] = info
        return func

    return deco
