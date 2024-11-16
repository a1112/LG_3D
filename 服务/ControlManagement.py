
import threading
from multiprocessing import Process
from threading import Thread

ThreadClass = Thread
ProcessClass = Process

BaseImageMosaic=threading.Thread

ImageSaverWorkNum=3
ImageSaverThreadType="thread"

D3SaverWorkNum=3
D3SaverThreadType="multiprocessing"

BaseDataFolder=ProcessClass