import requests
from server import write_plc,read_plc
import time
import datetime
from CoilDataBase.Coil import addToPlc,get_coil_by_coil_no


def add_plc(coil_No):
    coil_id = get_coil_by_coil_no(coil_No).Id
    addToPlc({
        "secondaryCoilId": coil_id,
        "location_S": read_plc("DB32.600", "int", 2),
        "location_L": read_plc("DB32.604", "int", 2),
        "location_laser": read_plc("DB32.0", "int", 2),
    })


oldId = ""

while True:

    try:
        addr = "DB35.40"
        data = requests.get("http://127.0.0.1:6005/currentCoil").json()
        # data={
        #     'act_w':1000
        #
        # }

        act_w = data["act_w"]
        old_w = read_plc(addr, "int", 2)

        if not oldId == data["Coil_ID"]:
            print(f"{datetime.datetime.now()} 新卷  {data['Coil_ID']}")
            add_plc(oldId)
            oldId = data["Coil_ID"]
        if not old_w == act_w:
            write_plc(addr,"int", data["act_w"])
            print(f"{datetime.datetime.now()}-> 写入 {addr}:   {data['act_w']}")
            print(data)
        time.sleep(3)
    except:
        time.sleep(5)
        print("PLC 写入失败/  数据获取失败")
