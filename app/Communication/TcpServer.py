import ctypes
import os
import threading
import time
from socket import (
    AF_INET,
    SOCK_STREAM,
    SOL_SOCKET,
    SO_REUSEADDR,
    timeout as SocketTimeout,
    socket,
)

import HttpServer
from DecodeData import Decode
from Log import logger

ADDRESS = "0.0.0.0"
PORT = 6001
BUFFER_SIZE = 1024


def _positive_float_env(name, default):
    try:
        return max(float(os.getenv(name, str(default))), 0.1)
    except ValueError:
        logger.warning("invalid %s, use default %s", name, default)
        return default


def _positive_int_env(name, default):
    try:
        return max(int(os.getenv(name, str(default))), 1)
    except ValueError:
        logger.warning("invalid %s, use default %s", name, default)
        return default


CLIENT_IDLE_TIMEOUT = _positive_float_env("LG3D_TCP_CLIENT_IDLE_TIMEOUT", 300.0)
MAX_CLIENTS = _positive_int_env("LG3D_TCP_MAX_CLIENTS", 128)
SERVER_BACKLOG = _positive_int_env("LG3D_TCP_BACKLOG", 128)
SERVER_RESTART_DELAY = _positive_float_env("LG3D_TCP_RESTART_DELAY", 2.0)
_client_slots = threading.BoundedSemaphore(MAX_CLIENTS)


def set_console_mode() -> None:
    try:
        kernel32 = ctypes.windll.kernel32
        handle = kernel32.GetStdHandle(-10)
        mode = ctypes.c_uint32()
        if not kernel32.GetConsoleMode(handle, ctypes.byref(mode)):
            return
        mode.value = (mode.value | 0x0080) & ~0x0040
        kernel32.SetConsoleMode(handle, mode.value)
    except AttributeError:
        logger.debug("skip console mode setup on non-Windows platform")


def tcplink(client_socket, addr, client_slot=None):
    logger.debug("Accept new connection from %s:%s...", addr[0], addr[1])
    try:
        client_socket.settimeout(CLIENT_IDLE_TIMEOUT)
        while True:
            try:
                data = client_socket.recv(BUFFER_SIZE)
            except SocketTimeout:
                logger.warning(
                    "close idle TCP client %s:%s after %.1fs",
                    addr[0],
                    addr[1],
                    CLIENT_IDLE_TIMEOUT,
                )
                break
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
        if client_slot is not None:
            client_slot.release()
        logger.debug("Connection from %s:%s closed.", addr[0], addr[1])


def run_tcp_server(stop_event=None) -> None:
    set_console_mode()
    HttpServer.start_http_server(stop_event)

    while stop_event is None or not stop_event.is_set():
        server_socket = socket(AF_INET, SOCK_STREAM)
        server_socket.setsockopt(SOL_SOCKET, SO_REUSEADDR, 1)
        server_socket.settimeout(1.0)
        try:
            server_socket.bind((ADDRESS, PORT))
            server_socket.listen(SERVER_BACKLOG)
            logger.info("start TCP server, listen ip:%s, port:%d", ADDRESS, PORT)
            while stop_event is None or not stop_event.is_set():
                try:
                    client_socket, client_address = server_socket.accept()
                except SocketTimeout:
                    continue
                if not _client_slots.acquire(blocking=False):
                    logger.warning(
                        "reject TCP client because limit reached: %s:%s max=%s",
                        client_address[0],
                        client_address[1],
                        MAX_CLIENTS,
                    )
                    client_socket.close()
                    continue
                thread = threading.Thread(
                    target=tcplink,
                    args=(client_socket, client_address, _client_slots),
                    daemon=True,
                    name=f"tcp-client-{client_address[0]}:{client_address[1]}",
                )
                try:
                    thread.start()
                except Exception:
                    _client_slots.release()
                    client_socket.close()
                    raise
        except OSError as exc:
            logger.exception("TCP server exception: %s", exc)
        finally:
            server_socket.close()

        if stop_event is not None and stop_event.is_set():
            break
        time.sleep(SERVER_RESTART_DELAY)


if __name__ == "__main__":
    run_tcp_server()
