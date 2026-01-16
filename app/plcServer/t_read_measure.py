import time

from server import read_plc


def read_measurements():
    distance = read_plc("DB35.340", "int", 4)
    axis1_pos = read_plc("DB32.600", "real", 4)
    axis2_pos = read_plc("DB32.604", "real", 4)
    print(f"distance(DB35.340)={distance}")
    print(f"axis1_pos(DB32.600)={axis1_pos}")
    print(f"axis2_pos(DB32.604)={axis2_pos}")


if __name__ == "__main__":
    while True:
        time.sleep(4)
        read_measurements()
