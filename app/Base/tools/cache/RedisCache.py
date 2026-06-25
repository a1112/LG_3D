import logging

import redis

logger = logging.getLogger(__name__)


def get_client():
    return redis.Redis(
            host='localhost',  # Redis 服务器地址
            port=6379,  # Redis 服务器端口
            db=0,  # 数据库编号
            password=None,  # 密码（如果有）
            decode_responses=True  # 自动解码返回值为字符串
        )

def ping():
    client = get_client()
    try:
        response = client.ping()
        logger.info("Redis connection ok: %s", response)
        return True
    except redis.ConnectionError as e:
        logger.warning("Redis connection failed: %s", e)
        return False

class RedisCache:

    def __init__(self):
        self.client = get_client()

