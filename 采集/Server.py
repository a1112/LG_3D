from threading import Thread
from fastapi import FastAPI, File, UploadFile
import uvicorn

import CONFIG

class CameraServer(Thread):
    def __init__(self, cameraInfo, cap):
        super().__init__()
        self.cameraInfo = cameraInfo
        self.cap = cap

    def run(self):


        app = FastAPI()
        @app.get("/getListenerAddFile")
        def getListenerAddFile():
            return self.cap.getCreatedFile()
        uvicorn.run(self.app, host=self.cameraInfo["serverIp"], port=self.cameraInfo["serverPort"])
def startServer(cameraInfo, cap):
    CameraServer(cameraInfo, cap).start()