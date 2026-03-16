import datetime
import time

import requests

from CoilDataBase.Coil import addToPlc, get_coil_by_coil_no
from server import read_plc, write_plc

CURRENT_COIL_URL = "http://127.0.0.1:6005/currentCoil"
PLC_WIDTH_ADDR = "DB35.40"
POLL_INTERVAL_SECONDS = 3
RETRY_INTERVAL_SECONDS = 5


def add_plc(coil_no):
    if not coil_no:
        return
    coil = get_coil_by_coil_no(coil_no)
    if coil is None:
        return
    addToPlc({
        "secondaryCoilId": coil.Id,
        "location_S": read_plc("M34", "real", 4),
        "location_L": read_plc("M38", "real", 4),
        "location_laser": read_plc("DB35.340", "int", 4),
    })


def get_current_coil():
    response = requests.get(CURRENT_COIL_URL, timeout=3)
    response.raise_for_status()
    data = response.json()
    if not isinstance(data, dict):
        raise ValueError(f"currentCoil 响应不是字典: {data}")
    return data


def get_act_w(data):
    for key in ("act_w", "ActWidth", "ACT_W", "width", "Width"):
        value = data.get(key)
        if value is not None:
            return int(value)
    return None


old_id = ""

while True:
    try:
        data = get_current_coil()
        coil_id = data.get("Coil_ID")
        act_w = get_act_w(data)

        if coil_id is None or act_w is None:
            print(f"{datetime.datetime.now()} currentCoil 缺少必要字段: {data}")
            time.sleep(POLL_INTERVAL_SECONDS)
            continue

        old_w = read_plc(PLC_WIDTH_ADDR, "int", 2)

        if old_id != coil_id:
            print(f"{datetime.datetime.now()} 新卷 {coil_id}")
            try:
                add_plc(old_id)
            except Exception:
                pass
            old_id = coil_id

        if old_w != act_w:
            write_plc(PLC_WIDTH_ADDR, "int", act_w)
            print(f"{datetime.datetime.now()} -> 写入 {PLC_WIDTH_ADDR}: {act_w}")
            print(data)

        time.sleep(POLL_INTERVAL_SECONDS)
    except Exception as e:
        print(e)
        time.sleep(RETRY_INTERVAL_SECONDS)
        print("PLC 写入失败 / 数据获取失败")
