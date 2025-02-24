import io
import time
from pathlib import Path

from PIL import Image
from fastapi import APIRouter
from fastapi.responses import StreamingResponse, FileResponse, Response

from CONFIG import serverConfigProperty
from tools.DataGet import DataGet, noFindImageByte
from .api_core import app
from tools.tool import expansion_box, bound_box

router = APIRouter(tags=["图像访问服务"])

@router.get("/image/preview/{surface_key:str}/{coil_id:str}/{type_:str}")
async def get_preview_image( surface_key, coil_id:str, type_: str, mask:bool = False):
    try:
        image_bytes = DataGet("preview", surface_key, coil_id, type_, mask).get_image()
        return Response(image_bytes, media_type="image/jpeg")
    except (Exception,) as e:
        print(e)
        return Response(content=noFindImageByte, media_type="image/jpeg")

@router.get("/image/source/{surface_key:str}/{coil_id:str}/{type_:str}")
async def get_image( surface_key, coil_id:str, type_: str, mask:bool = False):
    data_get = DataGet("source", surface_key, coil_id, type_, mask)
    # url = Path(data_get.get_source())
    image_bytes=data_get.get_image()
    if image_bytes is None:
        return None
    # print(f"图像获取 surface_key：{surface_key} coil_id：{coil_id} type_：{type_}  时间：{et-st}")
    # return FileResponse(str(url), media_type="image/png")
    # return StreamingResponse(io.BytesIO(image_bytes), media_type="image/png")
    # image = DataGet(source_type, surface_key, coil_id, type_, mask).get_image()
    # if image is None:
    #     return Response(content=noFindImageByte, media_type="image/jpeg")
    return Response(image_bytes, media_type="image/png")


@router.get("/defect_image/{surface_key:str}/{coil_id:int}/{type_:str}/{x:str}/{y:str}/{w:str}/{h:str}")
async def get_defect_image(surface_key, coil_id:int, type_: str, x:str, y:str, w:str, h:str):
    x, y, w, h = int(x), int(y), int(w),int(h)
    old_box = [x, y, w, h]
    image = DataGet("image", surface_key, coil_id, type_, False).get_image(pil=True)
    image:Image.Image
    if image is None:
        return Response(noFindImageByte, media_type="image/jpeg")

    x,y,w,h = expansion_box([x,y,w,h],image.size,expand_factor=0)
    # width, height = image.size
    # x1,y1,x2,y2 = x,y,x+w,y+h
    # x1,y1,x2,y2 = max(x1,0),max(y1,0),min(x2,width),min(y2,height)
    # x,y,w,h = x1, y1, x2-x1, y2-y1
    crop_image = image.crop((x,y,x+w,y+h))
    img_byte_arr = io.BytesIO()

    if bound_box([x,y,w,h],image.size):
        new_image = Image.new(crop_image.mode, (old_box[2], old_box[3]), (0, 0, 0))
        paste_x_y = (int((old_box[2] - w) / 2), int((old_box[3] - h) / 2))
        new_image.paste(crop_image, paste_x_y)
        new_image.paste(crop_image,paste_x_y)
        new_image.save(img_byte_arr, format='jpeg')
    else:
        crop_image.save(img_byte_arr, format='jpeg')
    img_byte_arr.seek(0)
    return StreamingResponse(img_byte_arr, media_type="image/png")


@router.get("/mesh/{surface_key:str}/{coil_id:str}")
async def get_mesh(surface_key, coil_id:str):
    mesh_file_path = DataGet("image", surface_key, coil_id, "mesh", False).get_mesh_source()
    return FileResponse(mesh_file_path, media_type='application/octet-stream')


@router.get("/coilInfo/{coil_id:str}/{surface_key:str}")
async def get_info(coil_id:str, surface_key:str):
    return serverConfigProperty.get_info(coil_id, surface_key)


@router.get("/preview/{surface_key:str}/{coil_id:str}/{type_:str}")
async def get_preview(surface_key, coil_id:str, type_: str):
    # return await get_image("preview",surface_key, coil_id,type_)
    url = serverConfigProperty.get_preview_file(coil_id, surface_key, type_)
    url = Path(url)
    if not url.exists():
        return Response(content=noFindImageByte, media_type="image/jpg")
    return FileResponse(str(url), media_type="image/jpg")
    #
    # with open(url, "rb") as image_file:
    #     image_data = image_file.read()
    #
    # return Response(content=image_data, media_type="image/jpg")

@router.get("/classifier_image/{surface_key:str}/{coil_id:str}/{url:str}")
async def get_classifier_image(surface_key,coil_id,url):
    image = DataGet("classifier_image", surface_key, coil_id, type_, False).get_image(pil=True)

app.include_router(router)

