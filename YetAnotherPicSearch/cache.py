import arrow
from tinydb import Query, TinyDB
from tinydb.operations import set

from .config import config


async def exist_in_cache(db: TinyDB, image_md5: str, mode: str) -> dict:
    cache_result = db.search((Query().image_md5 == image_md5) & (Query().mode == mode))
    if cache_result:
        db.update(
            set("update_at", arrow.now().for_json()), Query().image_md5 == image_md5
        )
        return cache_result[-1]
    else:
        return {}


async def clear_expired_cache(db: TinyDB) -> None:
    expired_date = arrow.now().shift(days=-config.cache_expire).for_json()
    db.remove(Query().update_at < expired_date)
