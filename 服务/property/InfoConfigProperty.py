

class InfoConfigProperty:
    def __init__(self, config:dict):
        self.config = config
        self.nextDict = self.config["nextDict"]

    def get_next(self, next_code):
        if isinstance(next_code, (int, float)):
            next_code = str(chr(int(next_code)))
        try:
            return self.nextDict[next_code]
        except KeyError:
            return f"未知代码 {next_code}"
