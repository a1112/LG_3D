import io
import time
from pathlib import Path

from PIL import Image
from fastapi import APIRouter
from fastapi.responses import StreamingResponse, FileResponse, Response

from CONFIG import serverConfigProperty
from property.Types import ImageType
from tools.DataGet import DataGet, noFindImageByte
from .api_core import app
from tools.tool import expansion_box, bound_box

router = APIRouter(tags=["图像访问服务"])


@router.get("/image/preview/{surface_key:str}/{coil_id:str}/{type_:str}")
async def get_preview_image(surface_key, coil_id: str, type_: str, mask: bool = False):
    try:
        image_bytes = DataGet("preview", surface_key, coil_id, type_, mask).get_image()
        return Response(image_bytes, media_type="image/jpeg")
    except (Exception,) as e:
        print(e)
        return Response(content=noFindImageByte, media_type="image/jpeg")


@router.get("/image/source/{surface_key:str}/{coil_id:str}/{type_:str}")
async def get_image(surface_key, coil_id: str, type_: str, mask: bool = False):
    """
    增加 2D 的 图像
    """
    data_get = DataGet("source", surface_key, coil_id, type_, mask)
    # url = Path(data_get.get_source())
    image_bytes = data_get.get_image()
    if image_bytes is None:
        return None
    # print(f"图像获取 surface_key：{surface_key} coil_id：{coil_id} type_：{type_}  时间：{et-st}")
    # return FileResponse(str(url), media_type="image/png")
    # return StreamingResponse(io.BytesIO(image_bytes), media_type="image/png")
    # image = DataGet(source_type, surface_key, coil_id, type_, mask).get_image()
    # if image is None:
    #     return Response(content=noFindImageByte, media_type="image/jpeg")
    return Response(image_bytes, media_type="image/jpeg")

@router.get("/image/area/{surface_key:str}/{coil_id:str}")
async def get_area_tiled(surface_key, coil_id: str,row=0, col=0, count=0):
    """
    当 row == -1 返回完整图像
    当 count == 0 返回宽高
    按照 count 分割返回图像
    """
    row=int(row)
    col=int(col)
    count=int(count)
    data_get = DataGet("source", surface_key, coil_id, "AREA", False)
    if row==-1:
        return Response(data_get.get_image(), media_type="image/jpeg")
    image = data_get.get_image(pil=True)
    w,h = image.size
    if count==0:
        return {
            "width":w,
            "height":h
        }
    w_width = w // count
    h_height = h // count
    crop_image = image.crop((row*w_width, col*h_height,(row+1)*w_width, (col+1)*h_height))
    img_byte_arr = io.BytesIO()
    crop_image.save(img_byte_arr, format='jpeg')
    img_byte_arr.seek(0)
    return StreamingResponse( img_byte_arr, media_type="image/png")

@router.get("/defect_image/{surface_key:str}/{coil_id:int}/{type_:str}/{x:str}/{y:str}/{w:str}/{h:str}")
async def get_defect_image(surface_key, coil_id: int, type_: str, x: str, y: str, w: str, h: str):
    x, y, w, h = int(x), int(y), int(w), int(h)
    old_box = [x, y, w, h]
    image = DataGet("image", surface_key, coil_id, type_, False).get_image(pil=True)
    image: Image.Image
    if image is None:
        return Response(noFindImageByte, media_type="image/jpeg")

    x, y, w, h = expansion_box([x, y, w, h], image.size, expand_factor=0)
    # width, height = image.size
    # x1,y1,x2,y2 = x,y,x+w,y+h
    # x1,y1,x2,y2 = max(x1,0),max(y1,0),min(x2,width),min(y2,height)
    # x,y,w,h = x1, y1, x2-x1, y2-y1
    crop_image = image.crop((x, y, x + w, y + h))
    img_byte_arr = io.BytesIO()

    if bound_box([x, y, w, h], image.size):
        new_image = Image.new(crop_image.mode, (old_box[2], old_box[3]), (0, 0, 0))
        paste_x_y = (int((old_box[2] - w) / 2), int((old_box[3] - h) / 2))
        new_image.paste(crop_image, paste_x_y)
        new_image.paste(crop_image, paste_x_y)
        new_image.save(img_byte_arr, format='jpeg')
    else:
        crop_image.save(img_byte_arr, format='jpeg')
    img_byte_arr.seek(0)
    return StreamingResponse(img_byte_arr, media_type="image/png")


@router.get("/mesh/{surface_key:str}/{coil_id:str}")
async def get_mesh(surface_key, coil_id: str):
    mesh_file_path = DataGet("image", surface_key, coil_id, "mesh", False).get_mesh_source()
    return FileResponse(mesh_file_path, media_type='application/octet-stream')


@router.get("/coilInfo/{coil_id:str}/{surface_key:str}")
async def get_info(coil_id: str, surface_key: str):
    return serverConfigProperty.get_info(coil_id, surface_key)


@router.get("/preview/{surface_key:str}/{coil_id:str}/{type_:str}")
async def get_preview(surface_key, coil_id: str, type_: str):
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


@router.get("/classifier_image/{coil_id:str}/{surface_key:str}/{class_name:str}/{x:int}/{y:int}/{w:int}/{h:int}")
async def get_classifier_image(coil_id, surface_key, class_name, x, y, w, h):
    #  http://127.0.0.1:5015/classifier_image/53956/S/背景_头尾/3188/5410/426/153
    #
    try:
        url = serverConfigProperty.get_classifier_image(coil_id, surface_key, class_name, x, y, w, h)
        return FileResponse(str(url), media_type="image/jpg")
    except StopIteration:
        data_get = DataGet("image", surface_key, coil_id, ImageType.GRAY, False)
        image = data_get.get_image(pil=True)

        if image is None:
            return Response(content=noFindImageByte, media_type="image/jpg")
        sub_image = image.crop((x, y, x + w, y + h))
        img_byte_arr = io.BytesIO()
        sub_image.save(img_byte_arr, format='jpeg')
        img_byte_arr.seek(0)
        return StreamingResponse(img_byte_arr, media_type="image/png")


app.include_router(router)
