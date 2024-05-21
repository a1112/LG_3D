import base64
from pathlib import Path

from PySide6 import QtCore
from PySide6.QtQuick import QQuickImageProvider
from PySide6.QtCore import QSize
from PySide6.QtGui import QPixmap
from icoextract import IconExtractor

from SoftList import globSoftList


class IconImageProvider(QQuickImageProvider):

    def __init__(self):
        QQuickImageProvider.__init__(self, QQuickImageProvider.Pixmap)

    def requestPixmap(self, id: str, size: QSize, requestedSize: QSize) -> QPixmap:
        try:
            if not id:
                return QPixmap()
            if id in globSoftList:
                id = globSoftList[id]["DisplayIcon"]
            id=id.replace("\"", "",999)
            id=id.replace("%5C","/",999)
            pixmap = QPixmap()
            if "," in id:
                id = id.split(",")[0]
            if ".ico" in id:
                pixmap.load(id)
                return pixmap
            ico_data = IconExtractor(id).get_icon(0)
            pixmap.loadFromData(ico_data.getvalue(), format='ico')
            pixmap = pixmap.scaled(256, 256)
            return pixmap
        except:
            return QPixmap()
            # print(globSoftList[id])



if __name__ == "__main__":
    import sys

    source = "C:\\Program Files\\Android\\Android Studio\\bin\\studio.exe"
    ico_data = IconExtractor(source).get_icon(0)
    with open("test.ico", "wb") as f:
        f.write(ico_data.getvalue())