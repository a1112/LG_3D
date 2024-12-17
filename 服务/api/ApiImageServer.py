import io
from pathlib import Path

from PIL import Image
from fastapi.responses import StreamingResponse, FileResponse, Response
from fastapi import APIRouter

from Globs import serverConfigProperty
from tools.DataGet import DataGet, noFindImageByte
from .api_core import app

router = APIRouter(tags=["图像访问服务"])

@router.get("/image/{source_type:str}/{surface_key:str}/{coil_id:str}/{type_:str}")
async def get_image(source_type, surface_key, coil_id:str, type_: str, mask:bool = False):

    url = serverConfigProperty.get_preview_file(coil_id, surface_key, type_)
    url = Path(url)
    url= Path(fr"F:\Data\Save_L\23001\mask\GRAY.png")
    print(url)
    if not url.exists():
        return Response(content=noFindImageByte, media_type="image/jpg")
    return FileResponse(str(url), media_type="image/png")

    # image = DataGet(source_type, surface_key, coil_id, type_, mask).get_image()
    # if image is None:
    #     return Response(content=noFindImageByte, media_type="image/jpeg")
    # return Response(image, media_type="image/png")


@router.get("/defect_image/{surface_key:str}/{coil_id:int}/{type_:str}/{x:int}/{y:int}/{w:int}/{h:int}")
async def get_defect_image(surface_key, coil_id:int, type_: str, x:int, y:int, w:int, h:int):
    image = DataGet("image", surface_key, coil_id, type_, False).get_image(pil=True)
    image:Image.Image
    if image is None:
        return Response(noFindImageByte, media_type="image/jpeg")
    crop_image = image.crop((x,y,x+w,y+h))
    img_byte_arr = io.BytesIO()
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
    url = serverConfigProperty.get_preview_file(coil_id, surface_key, type_)
    url = Path(url)
    print(url)
    if not url.exists():
        return Response(content=noFindImageByte, media_type="image/jpg")
    return FileResponse(str(url), media_type="image/jpg")

    #
    # with open(url, "rb") as image_file:
    #     image_data = image_file.read()
    #
    # return Response(content=image_data, media_type="image/jpg")

app.include_router(router)
