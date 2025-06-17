import redis

# 连接到 Redis
r = redis.Redis(host='localhost', port=6379, db=0)
print(r.ping())