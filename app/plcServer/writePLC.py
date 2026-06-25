import logging
import time

import requests

from CoilDataBase.Coil import addToPlc, get_coil_by_coil_no
from server import read_plc, write_plc

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s - %(message)s")
logger = logging.getLogger(__name__)

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


def main():
    old_id = ""
    while True:
        try:
            data = get_current_coil()
            coil_id = data.get("Coil_ID")
            act_w = get_act_w(data)

            if coil_id is None or act_w is None:
                logger.warning("currentCoil missing required fields: %s", data)
                time.sleep(POLL_INTERVAL_SECONDS)
                continue

            old_w = read_plc(PLC_WIDTH_ADDR, "int", 2)

            if old_id != coil_id:
                logger.info("new coil detected: %s", coil_id)
                try:
                    add_plc(old_id)
                except Exception as e:
                    logger.warning("add previous coil PLC snapshot failed: coil_id=%s error=%s", old_id, e)
                old_id = coil_id

            if old_w != act_w:
                write_plc(PLC_WIDTH_ADDR, "int", act_w)
                logger.info("wrote PLC width %s=%s for coil=%s", PLC_WIDTH_ADDR, act_w, coil_id)
                logger.debug("currentCoil payload: %s", data)

            time.sleep(POLL_INTERVAL_SECONDS)
        except Exception as e:
            logger.warning("PLC write or currentCoil fetch failed: %s", e)
            time.sleep(RETRY_INTERVAL_SECONDS)


if __name__ == "__main__":
    main()
