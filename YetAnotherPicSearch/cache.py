from pathlib import Path
from typing import Any, Dict, Iterator, List, MutableMapping, Optional, cast
from typing_extensions import override

import msgpack
from cookit import FileCacheManager
from cookit.loguru.common import logged_suppress
from nonebot_plugin_alconna.uniseg import UniMessage

from .config import config

# dumper and validators just works with simple standard UniMessages
# but it's enough for this plugin, maybe ¯\_(ツ)_/¯


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
            unpacked: List[List[Dict[str, Any]]] = msgpack.unpackb(data)
            return [UniMessage.load(x) for x in unpacked]
        return None

    @override
    def __setitem__(self, key: str, value: Optional[List[UniMessage]]) -> None:
        if not value:
            raise ValueError("value cannot be empty")
        data = None
        with logged_suppress("Failed to dump message cache"):
            dumped = [x.dump(media_save_dir=False) for x in value]
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
