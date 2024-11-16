

class InfoConfigProperty:
    def __init__(self, config:dict):
        self.config = config
        self.nextDict=self.config["nextDict"]
    def getNext(self,nextCode):
        try:
            return self.nextDict[nextCode]
        except KeyError:
            return f"未知代码 {nextCode}"