import io
from pathlib import Path

from PIL import Image
from starlette.responses import StreamingResponse

from tools.DataGet import DataGet, noFindImageByte
from fastapi import Response
from fastapi.responses import FileResponse
from .ApiBase import *


@app.get("/image/{sourceType:str}/{surfaceKey:str}/{coil_id:str}/{type_:str}")
async def get_image(sourceType,surfaceKey,coil_id:str, type_: str,mask:bool = False):
    image = DataGet(sourceType,surfaceKey,coil_id,type_,mask).get_image()
    if image is None:
        return Response(content=noFindImageByte, media_type="image/jpeg")
    return Response(image, media_type="image/png")


@app.get("/defect_image/{surfaceKey:str}/{coil_id:int}/{type_:str}/{x:int}/{y:int}/{w:int}/{h:int}")
async def get_defect_image(surfaceKey,coil_id:int, type_: str, x:int, y:int, w:int, h:int):
    image = DataGet("image",surfaceKey,coil_id,type_,False).get_image(pil=True)
    image:Image.Image
    if image is None:
        return Response(noFindImageByte, media_type="image/jpeg")
    cropImage = image.crop((x,y,x+w,y+h))
    img_byte_arr = io.BytesIO()
    cropImage.save(img_byte_arr, format='jpeg')
    img_byte_arr.seek(0)
    return StreamingResponse(img_byte_arr, media_type="image/png")


@app.get("/mesh/{surfaceKey:str}/{coil_id:str}")
async def get_mesh(surfaceKey,coil_id:str):
    MESH_FILE_PATH = DataGet("image",surfaceKey,coil_id,"mesh",False).get_mesh_source()
    return FileResponse(MESH_FILE_PATH, media_type='application/octet-stream')


@app.get("/coilInfo/{coil_id:str}/{surfaceKey:str}")
async def getInfo(coil_id:str, surfaceKey:str):
    return serverConfigProperty.get_info(coil_id, surfaceKey)


@app.get("/preview/{surfaceKey:str}/{coil_id:str}/{type_:str}")
async def get_preview(surfaceKey,coil_id:str, type_: str):
    url = serverConfigProperty.get_preview_file(coil_id,surfaceKey,type_)
    url = Path(url)
    if not url.exists():
        return Response(content=noFindImageByte, media_type="image/jpg")
    print(url)
    with open(url, "rb") as image_file:
        image_data = image_file.read()
    return Response(content=image_data, media_type="image/jpg")