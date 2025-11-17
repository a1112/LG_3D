import time

from sqlalchemy import false

from server import write_plc,read_plc


def reset():
    write_plc("M7.0","bool",True)
    write_plc("M20.0","bool",True)
    time.sleep(1)
    write_plc("M7.0","bool",False)
    write_plc("M20.0","bool",False)
    # write_plc("M7.0", "bool", False)
# reset()
def read_reset():
    m7d0 = read_plc("M7.0","bool",1)
    print(m7d0)
    m8d1 = read_plc("M8.1","bool",1)
    print(m8d1)
# reset()
read_reset()
# print(read_plc("DB27.4", "int", 2))
# print(read_plc("DB35.40", "int", 2))
#
# write_plc("DB35.40","int",1350)
# print(read_plc("DB35.40", "int", 2))
