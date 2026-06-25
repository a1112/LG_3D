import datetime
import struct

from DataSave import add_coil
from Log import logger

# short telCount; 2
# short sp00; 2
# char Coil_ID[16]; 16
# char Steel_Grade[20]; 20
# short act_w; 2
# short coil_dia; 2
# float FM_Tar_Thickness; 4
# int FM_Tar_Width; 2
# float sp01[10]; 40

DATA_PACKET_FORMAT = "3h2c16s20shhfhh10f"
DATA_PACKET_SIZE = struct.calcsize(DATA_PACKET_FORMAT)
currentCoil = {}


def DecodeHeartbeat(_data_):
    logger.debug("receive heartbeat packet: %s", _data_)


def DecodeData(_data_):
    global currentCoil
    if len(_data_) != DATA_PACKET_SIZE:
        logger.warning("invalid coil data packet length: %s, expected: %s", len(_data_), DATA_PACKET_SIZE)
        return None

    structData = struct.unpack(DATA_PACKET_FORMAT, _data_)
    logger.debug("receive coil data packet: %s", _data_)

    dataDict = {
        "len": structData[0],
        "head": structData[1],
        "telCount": structData[2],
        "outCode": structData[3],
        "sp00": structData[4],
        "Coil_ID": structData[5].decode("utf-8").strip().replace("\u0000", ""),
        "Steel_Grade": structData[6].decode("utf-8").strip(),
        "act_w": structData[7],
        "coil_dia": structData[8],
        "FM_Tar_Thickness": structData[9] / 1000,
        "FM_Tar_Width": structData[10],
        "coil_in_dia": structData[11],
        "sp01": structData[12:],
        "CreateTime": datetime.datetime.now(),
    }
    currentCoil = dataDict
    add_coil(dataDict)

    logger.debug("decoded coil data packet: %s", dataDict)
    return dataDict


def Decode(_data_):
    if len(_data_) > 50:
        return DecodeData(_data_)
    return DecodeHeartbeat(_data_)


if __name__ == "__main__":
    testData = "6000C35DF1000000345630353139323430300000000000005132333542202020202020202020202020202020ED0400000080F744E204000000000000000000000000000000000000000000000000000000000000000000000000000000000000"
    testData = bytes.fromhex(testData)
    DecodeData(testData)
