import redis

# 创建 Redis 连接
r = redis.Redis(
    host='localhost',  # Redis 服务器地址
    port=6379,        # Redis 服务器端口
    db=0,             # 数据库编号
    password=None,    # 密码（如果有）
    decode_responses=True  # 自动解码返回值为字符串
)

# 测试连接
try:
    response = r.ping()
    print("Redis 连接成功:", response)
except redis.ConnectionError:
    print("无法连接到 Redis 服务器")