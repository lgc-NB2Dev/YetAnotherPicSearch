from pathlib import Path
from typing import Any, Dict, Iterator, List, MutableMapping, Optional, Type, cast
from typing_extensions import override

import msgpack
from cookit import FileCacheManager
from cookit.loguru.common import logged_suppress
from cookit.pyd import type_dump_python
from nonebot_plugin_alconna.uniseg import Segment, UniMessage

from .config import config

# dumper and validators just works with simple standard UniMessages
# but it's enough for this plugin, maybe ¯\_(ツ)_/¯


def find_seg_class(seg_type: str) -> Type[Segment]:
    subclasses_will_find: List[Type[Segment]] = Segment.__subclasses__()
    while subclasses_will_find:
        now_will_find = subclasses_will_find.copy()
        subclasses_will_find.clear()
        for kls in now_will_find:
            if kls.__name__.lower() == seg_type:
                return kls
            subclasses_will_find.extend(kls.__subclasses__())
    raise ValueError(f"Segment type {seg_type} not found")


def segment_dumper(msg: Segment):
    data = msg.data.copy()
    del data["origin"]
    return {"type": msg.type, "data": type_dump_python(data)}


def segment_validator(data: Dict[str, Any]):
    seg_type = data["type"]
    kls = find_seg_class(seg_type)

    seg_data = data["data"].copy()
    # children = [segment_validator(x) for x in seg_data["_children"]]
    del seg_data["_children"]
    return kls(**seg_data)  # (*children)


def uni_message_dumper(msg: UniMessage):
    return [segment_dumper(x) for x in msg]


def uni_message_validator(data: List[Dict[str, Any]]):
    return UniMessage(segment_validator(x) for x in data)


class MessageCacheManager(MutableMapping[str, Optional[List[UniMessage]]]):
    def __init__(
        self,
        cache_dir: Path,
        max_size: Optional[int] = None,
        ttl: Optional[int] = None,
    ) -> None:
        super().__init__()
        self.cache = FileCacheManager(cache_dir, max_size=max_size, ttl=ttl)

    @override
    def __getitem__(self, key: str) -> Optional[List[UniMessage]]:
        data = self.cache[key]
        with logged_suppress("Failed to read message cache"):
            validated: List[List[Dict[str, Any]]] = msgpack.unpackb(data)
            return [uni_message_validator(x) for x in validated]
        return None

    @override
    def __setitem__(self, key: str, value: Optional[List[UniMessage]]) -> None:
        if not value:
            # del self.cache[key]
            return
        data = None
        with logged_suppress("Failed to dump message cache"):
            dumped = [uni_message_dumper(x) for x in value]
            data = cast(bytes, msgpack.packb(dumped))
        if data:
            self.cache[key] = data

    @override
    def __delitem__(self, key: str) -> None:
        self.cache.__delitem__(key)

    @override
    def __iter__(self) -> Iterator[str]:
        return self.cache.__iter__()

    @override
    def __len__(self) -> int:
        return self.cache.__len__()

    @override
    def __contains__(self, key: Any) -> bool:
        return self.cache.__contains__(key)


CACHE_DIR = Path.cwd() / "data" / "YetAnotherPicSearch" / "cache"
msg_cache = MessageCacheManager(
    CACHE_DIR,
    max_size=config.cache_expire * 100,
    ttl=config.cache_expire * 24 * 60 * 60,
)

# delete old cache
for _it in (x for x in Path.cwd().glob("pic_search_cache*") if x.is_file()):
    _it.unlink()
