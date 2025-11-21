import ctypes

kernel32 = ctypes.windll.kernel32
kernel32.SetConsoleMode(kernel32.GetStdHandle(-10), (0x4 | 0x80 | 0x20 | 0x2 | 0x10 | 0x1 | 0x00 | 0x100))

import os
import time
from socket import *
import threading
from DecodeData import Decode
from Log import logger
import HttpServer
address = '0.0.0.0'  # 监听哪些网络  127.0.0.1是监听本机 0.0.0.0是监听整个网络
port = 6001  # 监听自己的哪个端口
buffsize = 1024  # 接收从客户端发来的数据的缓存区大小
s = socket(AF_INET, SOCK_STREAM)
s.bind((address, port))
s.listen(2000)  # 最大连接数


def tcplink(sock, addr):
    logger.debug('Accept new connection from %s:%s...' % addr)
    while True:
        data = sock.recv(1024)
        if data == b'exit':
            break
        if len(data) == 0:
            break
        try:
            Decode(data)
        except:
            logger.debug("解析数据包失败"+str(data))

    sock.close()
    logger.debug('Connection from %s:%s closed.' % addr)


logger.debug("启动tcp服务,监听ip:%s,端口:%d" % (address, port))
logger.debug('Waiting for connection...')


try:
    while True:
        clientsock, clientaddress = s.accept()
        # 传输数据都利用clientsock，和s无关
        t = threading.Thread(target=tcplink, args=(clientsock, clientaddress))  # t为新创建的线程
        t.start()
        time.sleep(1)
except Exception as e:
    logger.debug(e)
    s.close()
    logger.debug("关闭 socket")
    time.sleep(2)

