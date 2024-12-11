from threading import Thread
from fastapi import FastAPI
import uvicorn

class CameraServer(Thread):
    def __init__(self, camera_info, cap):
        super().__init__()
        self.cameraInfo = camera_info
        self.cap = cap

    def run(self):
        app = FastAPI()

        @app.get("/getListenerAddFile")
        def get_listener_add_file():
            return self.cap.getCreatedFile()

        uvicorn.run(app, host=self.cameraInfo.serverIp, port=self.cameraInfo.serverPort)


def start_server(camera_info, cap):
    CameraServer(camera_info, cap).start()
