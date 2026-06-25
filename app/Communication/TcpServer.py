import ctypes
import threading
import time
from socket import AF_INET, SOCK_STREAM, socket

import HttpServer
from DecodeData import Decode
from Log import logger

kernel32 = ctypes.windll.kernel32
kernel32.SetConsoleMode(kernel32.GetStdHandle(-10), (0x4 | 0x80 | 0x20 | 0x2 | 0x10 | 0x1 | 0x00 | 0x100))

ADDRESS = "0.0.0.0"
PORT = 6001
BUFFER_SIZE = 1024

server_socket = socket(AF_INET, SOCK_STREAM)
server_socket.bind((ADDRESS, PORT))
server_socket.listen(2000)


def tcplink(client_socket, addr):
    logger.debug("Accept new connection from %s:%s..." % addr)
    while True:
        data = client_socket.recv(BUFFER_SIZE)
        if data == b"exit":
            break
        if len(data) == 0:
            break
        try:
            Decode(data)
        except Exception as e:
            logger.debug(f"decode packet failed: {e}; data={data!r}")

    client_socket.close()
    logger.debug("Connection from %s:%s closed." % addr)


logger.debug("start tcp server, listen ip:%s, port:%d" % (ADDRESS, PORT))
logger.debug("Waiting for connection...")

try:
    while True:
        client_socket, client_address = server_socket.accept()
        thread = threading.Thread(target=tcplink, args=(client_socket, client_address))
        thread.start()
        time.sleep(1)
except Exception as e:
    logger.debug(e)
    server_socket.close()
    logger.debug("close socket")
    time.sleep(2)
