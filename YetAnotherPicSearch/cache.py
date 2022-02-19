from io import BytesIO

import arrow
import httpx
import imagehash
from PIL import Image
from tinydb import Query, TinyDB
from tinydb.operations import set

from .config import config


async def get_imagehash_by_url(url: str, proxy: str) -> str:
    async with httpx.AsyncClient(proxies=proxy) as client:
        r = await client.get(url)
        im = Image.open(BytesIO(r.content))
        return str(imagehash.dhash(im))


async def exist_in_cache(db: TinyDB, image_hash: str, mode: str) -> dict:
    cache_result = db.search(
        (Query().image_hash == image_hash) & (Query().mode == mode)
    )
    if cache_result:
        db.update(
            set("update_at", arrow.now().for_json()), Query().image_hash == image_hash
        )
        return cache_result[-1]
    else:
        return {}


async def clear_expired_cache(db: TinyDB) -> None:
    expired_date = arrow.now().shift(days=-config.cache_expire).for_json()
    db.remove(Query().update_at < expired_date)
