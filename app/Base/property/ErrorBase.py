

class ServerDetectionException(Exception):
    def __init__(self, msg):
        super().__init__(f"服务检测报错: {msg}")
        self.msg=msg