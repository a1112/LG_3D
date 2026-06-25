import logging
import socket
import struct

logger = logging.getLogger(__name__)

DATA_PACKET_FORMAT = "3h2c16s20shhfhh10f"
TEST_PACKET = (
    b"`\x00\xc3]\xf1\t1\x004V06447300\x00\x00\x00\x00\x00\x00LGQX-HW             "
    b"\xef\x04\x04\x07\x00\xc0\x0fE\xe2\x04\xfa\x02\x00\x00\x00\x00\x00\x00\x00"
    b"\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00"
    b"\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00"
)


def send_test_packet(host: str = "127.0.0.1", port: int = 6001) -> None:
    struct_data = struct.unpack(DATA_PACKET_FORMAT, TEST_PACKET)
    logger.info("send tcp test packet to %s:%s: %s", host, port, struct_data)
    with socket.create_connection((host, port), timeout=5) as tcp_socket:
        tcp_socket.sendall(TEST_PACKET)


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s - %(message)s")
    send_test_packet()
