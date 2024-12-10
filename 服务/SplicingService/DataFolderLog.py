

class DataFolderLog:
    def __init__(self,folderLoader):
        self.folderLoader = folderLoader
        self.direction = folderLoader.direction
        self.saveFolder = str(folderLoader.saveFolder)
        self.folderConfig = folderLoader.folderConfig
        self.source = str(folderLoader.source)
        self.folderName = str(folderLoader.folderName)
        self.cropLeft = folderLoader.cropLeft
        self.cropRight = folderLoader.cropRight
