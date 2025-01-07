

class InfoConfigProperty:
    def __init__(self, config:dict):
        self.config = config
        self.nextDict = self.config["nextDict"]

    def getNext(self, next_code):
        try:
            return self.nextDict[next_code]
        except KeyError:
            return f"未知代码 {next_code}"
