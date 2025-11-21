from threading import Thread

class CameraControl(Thread):
    def __init__(self, capTrue):
        super().__init__()
        self.capTrue=capTrue