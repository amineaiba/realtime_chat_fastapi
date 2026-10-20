import logging

import redis.asyncio as redis

from core.config import get_settings

settings = get_settings()
logger = logging.getLogger(__name__)

# Async client, so Redis calls never block the event loop (Upstash in production).
redis_client = redis.from_url(settings.REDIS_URL, decode_responses=True)


async def set_user_online(user_id: str, ttl: int = 3600) -> None:
    """Mark user as online in Redis with TTL"""
    await redis_client.setex(f"user:{user_id}:status", ttl, "online")
    logger.debug("User %s marked online", user_id)


async def set_user_offline(user_id: str) -> None:
    """Mark user as offline in Redis"""
    await redis_client.delete(f"user:{user_id}:status")
    logger.debug("User %s marked offline", user_id)


async def is_user_online(user_id: str) -> bool:
    """Check if user is online"""
    return await redis_client.exists(f"user:{user_id}:status") > 0


async def blocklist_token(jti: str, ttl_seconds: int) -> None:
    """Blocklist an access token's jti until it would have expired anyway"""
    if ttl_seconds <= 0:
        return
    await redis_client.setex(f"blocklist:{jti}", ttl_seconds, "1")


async def is_token_blocklisted(jti: str | None) -> bool:
    """Check if an access token's jti has been revoked (e.g. via logout)"""
    if not jti:
        return False
    return await redis_client.exists(f"blocklist:{jti}") > 0
