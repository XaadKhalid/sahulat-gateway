from arq.connections import ArqRedis, RedisSettings, create_pool

from app.core.config import RedisSettings as AppRedisSettings

# Global cache for redis pool
_redis_pool: ArqRedis | None = None


async def get_redis_pool(settings: AppRedisSettings) -> ArqRedis:
    global _redis_pool
    if _redis_pool is None:
        url = settings.redis_url.get_secret_value()
        arq_settings = RedisSettings.from_dsn(url)
        _redis_pool = await create_pool(arq_settings)
    return _redis_pool
