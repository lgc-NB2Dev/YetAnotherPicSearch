from typing import List, Optional

from diskcache import Cache

from .config import config


def upsert_cache(cache: Cache, image_md5: str, mode: str, result: List[str]) -> None:
    cache.set(f"{image_md5}_{mode}", result, expire=config.cache_expire * 24 * 60 * 60)


def exist_in_cache(cache: Cache, image_md5: str, mode: str) -> Optional[List[str]]:
    cache_result: Optional[List[str]] = cache.get(f"{image_md5}_{mode}")
    if cache_result:
        cache.touch(f"{image_md5}_{mode}", expire=config.cache_expire * 24 * 60 * 60)
    return cache_result
