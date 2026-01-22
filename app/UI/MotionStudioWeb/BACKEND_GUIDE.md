# 后端动态图像接口实现指南

## 概述

前端已实现基于显示器尺寸的渐进式图像加载，需要后端支持返回不同尺寸的图像。

## 前端请求格式

前端会在图像URL中添加以下查询参数：

```
/api/image/preview/{surface_key}/{coil_id}/{type}?width=800&height=600&quality=85&format=jpg
```

### 参数说明

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `width` | int | 否 | 目标宽度（像素） |
| `height` | int | 否 | 目标高度（像素） |
| `quality` | int | 否 | JPEG质量 (1-100)，默认85 |
| `format` | string | 否 | 输出格式 (jpg/png/webp)，默认jpg |

## 后端实现方案

### 方案一：使用 Pillow 实时调整

在 `app/Server/api/ApiImageServer.py` 中添加尺寸参数支持：

```python
from fastapi import Query
from PIL import Image
from io import BytesIO
import numpy as np

@api.get("/image/preview/{surface_key}/{coil_id}/{type_}")
async def get_preview_image(
    surface_key: str,
    coil_id: int,
    type_: str,
    width: int = Query(None, description="目标宽度"),
    height: int = Query(None, description="目标高度"),
    quality: int = Query(85, ge=1, le=100, description="JPEG质量"),
    format: str = Query("jpg", regex="^(jpg|png|webp)$", description="输出格式")
):
    """
    获取预览图像，支持动态尺寸调整
    """
    try:
        # 1. 获取原始图像数据
        original_image_data = get_original_image_data(surface_key, coil_id, type_)

        # 2. 使用Pillow打开图像
        img = Image.open(BytesIO(original_image_data))

        # 3. 计算目标尺寸（保持宽高比）
        if width or height:
            original_width, original_height = img.size

            if width and height:
                # 同时指定宽高
                target_size = (width, height)
            elif width:
                # 只指定宽度，按比例计算高度
                ratio = width / original_width
                target_size = (width, int(original_height * ratio))
            else:
                # 只指定高度，按比例计算宽度
                ratio = height / original_height
                target_size = (int(original_width * ratio), height)

            # 使用高质量的缩放算法
            img = img.resize(target_size, Image.Resampling.LANCZOS)

        # 4. 转换为RGB（如果是RGBA）
        if img.mode == 'RGBA':
            # 创建白色背景
            background = Image.new('RGB', img.size, (255, 255, 255))
            background.paste(img, mask=img.split()[3])  # 使用alpha通道作为mask
            img = background
        elif img.mode != 'RGB':
            img = img.convert('RGB')

        # 5. 保存到字节流
        output = BytesIO()

        if format == 'png':
            img.save(output, format='PNG', optimize=True)
        elif format == 'webp':
            img.save(output, format='WEBP', quality=quality)
        else:  # jpg
            img.save(output, format='JPEG', quality=quality, optimize=True)

        output.seek(0)

        # 6. 返回图像
        media_type = f"image/{format}"
        return Response(content=output.read(), media_type=media_type)

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
```

### 方案二：使用 OpenCV（更快）

```python
import cv2
import numpy as np

@api.get("/image/preview/{surface_key}/{coil_id}/{type_}")
async def get_preview_image_cv2(
    surface_key: str,
    coil_id: int,
    type_: str,
    width: int = Query(None),
    height: int = Query(None),
    quality: int = Query(85, ge=1, le=100),
    format: str = Query("jpg", regex="^(jpg|png|webp)$")
):
    """
    使用OpenCV进行图像处理（更快）
    """
    try:
        # 1. 获取原始图像数据
        original_image_data = get_original_image_data(surface_key, coil_id, type_)

        # 2. 解码图像
        nparr = np.frombuffer(original_image_data, np.uint8)
        img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)

        # 3. 调整尺寸
        if width or height:
            original_height, original_width = img.shape[:2]

            if width and height:
                target_size = (width, height)
            elif width:
                ratio = width / original_width
                target_size = (width, int(original_height * ratio))
            else:
                ratio = height / original_height
                target_size = (int(original_width * ratio), height)

            # 使用INTER_AREA进行缩小（最好质量），INTER_CUBIC用于放大
            interpolation = cv2.INTER_AREA if (width or width) < original_width else cv2.INTER_CUBIC
            img = cv2.resize(img, target_size, interpolation=interpolation)

        # 4. 编码图像
        encode_param = [int(cv2.IMWRITE_JPEG_QUALITY), quality]

        if format == 'png':
            encode_param = [int(cv2.IMWRITE_PNG_COMPRESSION), 9]
            ext = '.png'
        elif format == 'webp':
            encode_param = [int(cv2.IMWRITE_WEBP_QUALITY), quality]
            ext = '.webp'
        else:
            ext = '.jpg'

        result, encoded_img = cv2.imencode(ext, img, encode_param)

        if not result:
            raise HTTPException(status_code=500, detail="Failed to encode image")

        # 5. 返回图像
        media_type = f"image/{format}"
        return Response(content=encoded_img.tobytes(), media_type=media_type)

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
```

### 方案三：缓存优化（推荐）

为了避免重复处理相同尺寸，可以添加缓存层：

```python
from functools import lru_cache
import hashlib

# 缓存管理
image_cache = {}

def get_cache_key(surface_key: str, coil_id: int, type_: str, width: int, height: int, quality: int, format: str) -> str:
    """生成缓存键"""
    data = f"{surface_key}_{coil_id}_{type_}_{width}_{height}_{quality}_{format}"
    return hashlib.md5(data.encode()).hexdigest()

@api.get("/image/preview/{surface_key}/{coil_id}/{type_}")
async def get_preview_image_cached(
    surface_key: str,
    coil_id: int,
    type_: str,
    width: int = Query(None),
    height: int = Query(None),
    quality: int = Query(85),
    format: str = Query("jpg")
):
    """
    带缓存的图像接口
    """
    cache_key = get_cache_key(surface_key, coil_id, type_, width, height, quality, format)

    # 检查缓存
    if cache_key in image_cache:
        cached_data, cached_time = image_cache[cache_key]
        # 缓存有效期30分钟
        if time.time() - cached_time < 1800:
            media_type = f"image/{format}"
            return Response(content=cached_data, media_type=media_type)

    # 处理图像...
    result_data = process_image(...)

    # 存入缓存（限制缓存大小）
    if len(image_cache) > 1000:  # 最多缓存1000个图像
        # 删除最旧的100个
        oldest_keys = sorted(image_cache.items(), key=lambda x: x[1][1])[:100]
        for key in oldest_keys:
            del image_cache[key[0]]

    image_cache[cache_key] = (result_data, time.time())

    return Response(content=result_data, media_type=f"image/{format}")
```

## 性能优化建议

### 1. 异步处理

对于大图像，可以使用后台任务处理：

```python
from fastapi import BackgroundTasks

processing_tasks = {}

@api.get("/image/preview/{surface_key}/{coil_id}/{type_}")
async def get_preview_image_async(
    surface_key: str,
    coil_id: int,
    type_: str,
    width: int = Query(None),
    height: int = Query(None),
    background_tasks: BackgroundTasks
):
    cache_key = get_cache_key(...)

    # 如果正在处理中，等待
    if cache_key in processing_tasks:
        await processing_tasks[cache_key].wait()
        return get_cached_image(cache_key)

    # 如果已有缓存，直接返回
    if cache_key in image_cache:
        return get_cached_image(cache_key)

    # 添加处理任务
    task = ImageProcessingTask(cache_key, ...)
    processing_tasks[cache_key] = task
    background_tasks.add_task(task.process)

    # 先返回低质量版本
    return get_low_quality_preview(surface_key, coil_id, type_)
```

### 2. 使用多级缓存

```python
# L1: 内存缓存（最近使用的）
memory_cache = {}

# L2: 磁盘缓存
import diskcache
disk_cache = diskcache.Cache('./image_cache')

async def get_image_with_multilevel_cache(cache_key: str):
    # 先查内存
    if cache_key in memory_cache:
        return memory_cache[cache_key]

    # 再查磁盘
    if cache_key in disk_cache:
        data = disk_cache[cache_key]
        memory_cache[cache_key] = data
        return data

    # 处理并缓存
    data = await process_image(...)
    disk_cache[cache_key] = data
    memory_cache[cache_key] = data

    return data
```

### 3. 使用 CDN

对于生产环境，建议：
1. 处理后的图像上传到CDN
2. 前端直接从CDN获取
3. 使用CDN的图像处理功能（如阿里云OSS、腾讯云COS）

## 测试接口

### 测试不同尺寸

```bash
# 原始尺寸
curl "http://localhost:8000/api/image/preview/top/1/preview"

# 指定宽度（高度自动计算）
curl "http://localhost:8000/api/image/preview/top/1/preview?width=800"

# 指定高度（宽度自动计算）
curl "http://localhost:8000/api/image/preview/top/1/preview?height=600"

# 同时指定宽高
curl "http://localhost:8000/api/image/preview/top/1/preview?width=800&height=600"

# 指定质量
curl "http://localhost:8000/api/image/preview/top/1/preview?width=800&quality=60"

# 不同格式
curl "http://localhost:8000/api/image/preview/top/1/preview?width=800&format=webp"
```

## 监控和日志

添加性能监控：

```python
import time
from fastapi import Request

@app.middleware("http")
async def monitor_image_requests(request: Request, call_next):
    if request.url.path.startswith("/api/image/"):
        start_time = time.time()

        response = await call_next(request)

        process_time = time.time() - start_time
        size = len(response.body)

        # 记录日志
        logger.info(
            f"Image request: {request.url.params} - "
            f"Time: {process_time:.3f}s - Size: {size/1024:.1f}KB"
        )

        # 添加响应头
        response.headers["X-Process-Time"] = str(process_time)
        response.headers["X-Image-Size"] = str(size)

    return response
```

## 总结

1. **最小改动**: 只需添加查询参数支持，使用Pillow或OpenCV调整尺寸
2. **性能优化**: 添加缓存层，避免重复处理
3. **生产就绪**: 考虑使用CDN和异步处理
4. **监控**: 添加性能监控和日志

前端已经完全支持动态尺寸加载，后端只需按照上述方案实现即可。
