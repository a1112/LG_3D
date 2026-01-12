import time

from server import read_plc


def read_measurements():
    distance = read_plc("DB32.340", "real", 4)
    axis1_pos = read_plc("M34", "real", 4)
    axis2_pos = read_plc("M38", "real", 4)
    print(f"distance(DB32.340)={distance}")
    print(f"axis1_pos(MD34)={axis1_pos}")
    print(f"axis2_pos(MD38)={axis2_pos}")


if __name__ == "__main__":
    while True:
        time.sleep(4)
        read_measurements()
