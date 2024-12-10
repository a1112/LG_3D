"""
记录服务器日志

"""


class ServerMsg:
    """
    通讯，日志记录
    """

    def __init__(self):
        self.msgDict = {}
        self.msgList = []

    def addMsg(self, msgType, msg):
        self.msgList.append([msgType, msg])
        self.msgDict[msgType] = msg

    def getLastMsg(self, msgType=None):
        if msgType:
            if msgType in self.msgDict:
                return self.msgDict[msgType]
        else:
            if len(self.msgList) > 0:
                return self.msgList[-1]
        return None

    def getAllType(self):
        return list(self.msgDict.keys())
