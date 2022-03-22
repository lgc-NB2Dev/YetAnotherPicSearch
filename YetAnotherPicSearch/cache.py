from typing import List, Optional

import arrow
from tinydb import Query, TinyDB
from tinydb.operations import set
from tinydb.table import Document

from .config import config
from .result import Result


async def exist_in_cache(db: TinyDB, image_md5: str, mode: str) -> Optional[Result]:
    result: Optional[Result] = None
    cache_result: List[Document] = db.search(
        (Query().image_md5 == image_md5) & (Query().mode == mode)
    )
    if cache_result:
        db.update(
            set("update_at", arrow.now().for_json()), Query().image_md5 == image_md5  # type: ignore
        )
        result = Result(cache_result[-1])
    return result


async def clear_expired_cache(db: TinyDB) -> None:
    expired_date = arrow.now().shift(days=-config.cache_expire).for_json()
    db.remove(Query().update_at < expired_date)
