from HslCommunication import SiemensS7Net, SiemensPLCS
from snap7.util import get_int, get_real, get_dword, get_string, get_byte, get_word, get_bool
from fastapi import FastAPI
import config

app = FastAPI()


def getSiemens(PLC_IP, PLC_RACK, PLC_SLOT):

    siemens = SiemensS7Net(SiemensPLCS.S400, PLC_IP)
    siemens.SetSlotAndRack(PLC_RACK, PLC_SLOT)
    return siemens


siemens = None


def getValue(value, typeStr):
    if typeStr == "int":
        return get_int(value, 0)
    elif typeStr == "real":
        return get_real(value, 0)
    elif typeStr == "dword":
        return get_dword(value, 0)
    elif typeStr == "string":
        return value.decode("utf-8")
    elif typeStr == "bytes":
        return bytes(value)
    elif typeStr == "word":
        return get_word(value, 0)
    elif typeStr == "bool":
        return get_bool(value, 0, 0)
    else:
        raise


@app.get("/plc/info/")
def info_plc():
    return {
        "typeList": ["int", "real", "dword", "string", "bytes", "word", "bool"],
        "plc_ip": config.plcForwarderUrl,
        "rack": config.plcForwarderRack,
        "slot": config.plcForwarderSlot
    }


@app.get("/plc/connect/(plc_ip)/(rack)/(slot)")
def connect_plc(plc_ip: str, rack: int, slot: int):
    global siemens
    config.plcForwarderUrl = plc_ip
    config.plcForwarderRack = rack
    config.plcForwarderSlot = slot
    siemens = getSiemens(plc_ip, rack, slot)
    return True


@app.get("/plc/get/{addr}/{typeStr}/{length}")
def forward_request(addr: str, typeStr: str, length: int):
    global siemens
    if siemens is None:
        siemens = getSiemens(config.plcForwarderUrl, config.plcForwarderRack, config.plcForwarderSlot)
    value = siemens.Read(addr, length).Content
    return getValue(value, typeStr)


def read_plc(addr, typeStr, length):
    return forward_request(addr, typeStr, length)


def write_plc(addr,typeStr,value):
    global siemens
    if siemens is None:
        siemens = getSiemens(config.plcForwarderUrl, config.plcForwarderRack, config.plcForwarderSlot)
    if typeStr == 'int':
        return siemens.WriteInt16(addr,value)
    if typeStr == 'word':
        return siemens.WriteDouble(addr,value)
    raise
