import datetime
import struct

from Log import logger
from DataSave import add_coil

# short      telCount;         2
# short		sp00;	           2                /* spare */
# char		Coil_ID[16];       16               /* Coil No;Alpha-numeric */
# char    	Steel_Grade[20];   20           	/*Coil Steel Grade*/
# short   	act_w;             2               	/* 实际宽度<mm> */
# short   	coil_dia;          2        	    /* 卷径 <mm> */
# float    	FM_Tar_Thickness;  4        	    /*FM_TAR_Thickness;mm;成品厚度*/
# int	    FM_Tar_Width;      2            	/*FM_TAR_Width;mm;成品宽度*/
# float		sp01[10];		   40		        /* SPARE */

currentCoil = {}


def DecodeHeartbeat(_data_):
    logger.debug("接收到心跳包: " + str(_data_))


def DecodeData(_data_):
    global currentCoil
    print(len(_data_))
    structData = struct.unpack("3h2c16s20shhfhh10f", _data_)
    logger.debug("接收到数据包: " + str(_data_))

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
        "CreateTime": datetime.datetime.now()
    }
    currentCoil = dataDict
    add_coil(dataDict)

    logger.debug("解析数据包: " + str(dataDict))


def Decode(_data_):
    if len(_data_) > 50:
        return DecodeData(_data_)
    else:
        return DecodeHeartbeat(_data_)


if __name__ == "__main__":
    testData = "6000C35DF1000000345630353139323430300000000000005132333542202020202020202020202020202020ED0400000080F744E204000000000000000000000000000000000000000000000000000000000000000000000000000000000000"
    # class Data(Structure):
    #     _fields_ = [
    #         ("telCount", c_short),
    #         ("sp00", c_short),
    #         ("Coil_ID", c_char*16),
    #         ("Steel_Grade", c_char*20),
    #         ("act_w", c_short),
    #         ("coil_dia", c_short),
    #         ("FM_Tar_Thickness", c_float),
    #         ("FM_Tar_Width", c_int),
    #         ("sp01", c_float*10)
    #     ]
    # data = Data()
    testData = bytes.fromhex(testData)
    print(testData)
    data = DecodeData(testData)
    print(data)
    data_ = {'h0': 96,
             'h1': 24003,
             'telCount': 241,
             'sp00': 0,
             'Coil_ID': '4V05192400\x00\x00\x00\x00\x00\x00',
             'Steel_Grade': 'Q235B',
             'act_w': 1261,
             'coil_dia': 0,
             'FM_Tar_Thickness': 1980.0,
             'FM_Tar_Width': 1250,
             'sp01': (0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0)
             }
