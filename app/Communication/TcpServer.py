import ctypes
import threading
import time
from socket import AF_INET, SOCK_STREAM, socket

import HttpServer
from DecodeData import Decode
from Log import logger

ADDRESS = "0.0.0.0"
PORT = 6001
BUFFER_SIZE = 1024


def set_console_mode() -> None:
    try:
        kernel32 = ctypes.windll.kernel32
        kernel32.SetConsoleMode(kernel32.GetStdHandle(-10), (0x4 | 0x80 | 0x20 | 0x2 | 0x10 | 0x1 | 0x00 | 0x100))
    except AttributeError:
        logger.debug("skip console mode setup on non-Windows platform")


def tcplink(client_socket, addr):
    logger.debug("Accept new connection from %s:%s...", addr[0], addr[1])
    try:
        while True:
            data = client_socket.recv(BUFFER_SIZE)
            if data == b"exit":
                break
            if len(data) == 0:
                break
            try:
                Decode(data)
            except Exception as exc:
                logger.debug("decode packet failed: %s; data=%r", exc, data)
    finally:
        client_socket.close()
        logger.debug("Connection from %s:%s closed.", addr[0], addr[1])


def run_tcp_server() -> None:
    set_console_mode()
    HttpServer.start_http_server()

    server_socket = socket(AF_INET, SOCK_STREAM)
    server_socket.bind((ADDRESS, PORT))
    server_socket.listen(2000)
    logger.debug("start tcp server, listen ip:%s, port:%d", ADDRESS, PORT)
    logger.debug("Waiting for connection...")
    try:
        while True:
            client_socket, client_address = server_socket.accept()
            thread = threading.Thread(target=tcplink, args=(client_socket, client_address), daemon=True)
            thread.start()
    except Exception as exc:
        logger.debug("tcp server exception: %s", exc)
        server_socket.close()
        logger.debug("close socket")
        time.sleep(2)


if __name__ == "__main__":
    run_tcp_server()
