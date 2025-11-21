import os
import time

from fastapi import UploadFile, File, APIRouter
from fastapi.responses import FileResponse, StreamingResponse

from .api_core import app

router = APIRouter(tags=["测试服务"])


@router.get("/download_test")
async def download_file():
    file_path = "./test/zipdir.zip"
    if os.path.exists(file_path):
        return FileResponse(path=file_path, filename="downloaded_file.zip", media_type='application/octet-stream')
    else:
        return {"error": "File not found"}


# 测试下载速度的接口
@router.get("/speedtest/download")
async def download_test(size_in_mb: int = 10):
    """
    生成一个指定大小的文件流，单位是MB（默认为10MB）
    访问此接口可测试下载速度。
    """
    chunk_size = 1024 * 1024  # 1MB
    total_chunks = size_in_mb

    # 生成指定大小的数据块
    def generate_data():
        data = b"0" * chunk_size
        for _ in range(total_chunks):
            yield data

    return StreamingResponse(generate_data(), media_type="application/octet-stream")


# 测试上传速度的接口
@router.post("/speedtest/upload")
async def upload_test(file: UploadFile = File(...)):
    """
    接收文件并记录上传时间。
    访问此接口上传文件可测试上传速度。
    """
    start_time = time.time()
    # 读取上传的文件内容
    content = await file.read()
    end_time = time.time()

    file_size = len(content) / (1024 * 1024)  # 文件大小（MB）
    upload_time = end_time - start_time  # 上传时间（秒）
    upload_speed = file_size / upload_time  # 上传速度（MB/s）

    return {
        "filename": file.filename,
        "file_size_mb": round(file_size, 2),
        "upload_time_s": round(upload_time, 2),
        "upload_speed_mb_s": round(upload_speed, 2)
    }


app.include_router(router)