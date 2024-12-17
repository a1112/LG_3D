from fastapi import FastAPI, Response
from fastapi.responses import StreamingResponse
from redis import Redis
from io import BytesIO
from minio import Minio

app = FastAPI()

# 初始化 Redis 缓存
redis_client = Redis(host="localhost", port=6379, decode_responses=True)

# 初始化 MinIO 客户端
minio_client = Minio(
    "localhost:9000",
    access_key="YOUR_ACCESS_KEY",
    secret_key="YOUR_SECRET_KEY",
    secure=False,
)

BUCKET_NAME = "images"

@app.get("/image/{image_name}")
async def get_image(image_name: str):
    # 1. 尝试从 Redis 缓存获取图像
    cached_image = redis_client.get(image_name)
    if cached_image:
        return StreamingResponse(BytesIO(cached_image), media_type="image/png")

    # 2. 从 MinIO 获取图像
    try:
        response = minio_client.get_object(BUCKET_NAME, image_name)
        image_data = response.read()

        # 3. 缓存到 Redis
        redis_client.setex(image_name, 3600, image_data)  # 设置缓存 1 小时

        # 4. 返回图像
        return StreamingResponse(BytesIO(image_data), media_type="image/png")
    except Exception as e:
        return Response(content="Image not found", status_code=404)
