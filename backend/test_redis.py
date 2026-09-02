import asyncio
from app2.core.redis import get_redis


async def main():
    redis = await get_redis()

    try:
        result = await redis.ping()
        print("Redis:", result)
    finally:
        await redis.aclose()


asyncio.run(main())