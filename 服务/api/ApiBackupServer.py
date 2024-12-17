import json
from fastapi import WebSocket, APIRouter
from CoilDataBase import backup
from utils import Backup
from .api_core import app
from Globs import serverConfigProperty


router = APIRouter(tags=["备份服务"])


@router.get("/save_to_sql/{sql_file:path}")
def save_to_sql(sql_file: str):
    state=False
    if ".sql" in sql_file.lower():
        state = backup.backup_to_sql(sql_file, mysqldump_exe=serverConfigProperty.mysqldump_exe)
    if ".db" in sql_file.lower():
        state = backup.backup_to_sqlite(sql_file)
    return {"state": state}

@router.websocket("/ws/backupImageTask")
async def ws_backup_image_task(websocket: WebSocket):
    await websocket.accept()
    while True:
        try:
            # 接收客户端发送的消息
            data = await websocket.receive_text()
            data = json.loads(data)
            from_id = data['from_id']
            to_id = data['to_id']
            save_folder = data['folder']

            async def msgFunc_(value):
                await websocket.send_text(str(value))

            await Backup.backup_image_task(from_id, to_id, save_folder)
            # 处理并响应数据
            await websocket.send_text(str(100))

        except Exception as e:
            print(f"Connection error: {e}")
            break

app.include_router(router)
