#  encoding = utf-8
import os

from PySide6.QtCore import Slot, QObject, QUrl, QMimeData
from PySide6.QtGui import QGuiApplication, QClipboard, QImage


class Clipboard(QObject):

    @Slot(str, result=bool)
    def setText(self, text: str):
        return QGuiApplication.clipboard().setText(text)

    @Slot(result=str)
    def text(self):
        return QGuiApplication.clipboard().text()

    @Slot(QUrl, result=bool)
    @Slot(str, result=bool)
    def setImageByUrl(self, url):
        if isinstance(url, QUrl):
            return QGuiApplication.clipboard().setImage(QImage(url.path()[1:]))
        else:
            return QGuiApplication.clipboard().setImage(QImage(url))

    @Slot(QUrl)
    @Slot(str)
    def setUrl(self, url):
        url = QUrl(url)
        mimeDate = QMimeData()
        mimeDate.setUrls([url])
        QGuiApplication.clipboard().setMimeData(mimeDate)
