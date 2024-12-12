from pathlib import Path

from tools.DataGet import DataGet, noFindImageByte
from .api_core import app
from Globs import serverConfigProperty
from fastapi import Response
from fastapi.responses import FileResponse


@app.get("/image/{sourceType:str}/{surfaceKey:str}/{coil_id:str}/{type_:str}")
async def get_image(sourceType,surfaceKey,coil_id:str, type_: str,mask:bool = False):
    image = DataGet(sourceType,surfaceKey,coil_id,type_,mask).get_image()
    if image is None:
        return Response(content=noFindImageByte, media_type="image/jpeg")
    return Response(image, media_type="image/png")


@app.get("/mesh/{surfaceKey:str}/{coil_id:str}")
async def get_mesh(surfaceKey,coil_id:str):
    MESH_FILE_PATH = DataGet("image",surfaceKey,coil_id,"mesh",False).get_mesh_source()
    return FileResponse(MESH_FILE_PATH, media_type='application/octet-stream')


@app.get("/coilInfo/{coil_id:str}/{surfaceKey:str}")
async def getInfo(coil_id:str, surfaceKey:str):
    return serverConfigProperty.get_Info(coil_id,surfaceKey)


@app.get("/preview/{surfaceKey:str}/{coil_id:str}/{type_:str}")
def get_preview(surfaceKey,coil_id:str, type_: str):
    url = serverConfigProperty.get_preview_file(coil_id,surfaceKey,type_)
    url = Path(url)
    if not url.exists():
        return Response(content=noFindImageByte, media_type="image/jpg")
    print(url)
    with open(url, "rb") as image_file:
        image_data = image_file.read()
    return Response(content=image_data, media_type="image/jpg")