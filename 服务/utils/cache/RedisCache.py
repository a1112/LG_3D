from fastapi import FastAPI
from fastapi_cache import caches, close_caches
from fastapi_cache.backends.redis import RedisCacheBackend
from redis import asyncio as aioredis

app = FastAPI()

# 配置Redis缓存后端
cache_backend = RedisCacheBackend(host="localhost", port=6379, db=0, password=None)
caches.set_custom_cache(cache_backend)


@app.on_event("startup")
async def startup():
    await cache_backend.client.ping()  # 测试连接


@app.on_event("shutdown")
async def shutdown():
    await close_caches()
