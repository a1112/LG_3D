import ctypes
kernel32 = ctypes.windll.kernel32
kernel32.SetConsoleMode(kernel32.GetStdHandle(-10), (0x4 | 0x80 | 0x20 | 0x2 | 0x10 | 0x1 | 0x00 | 0x100))

if __name__=="__main__":
    from HslCommunication import SiemensS7Net, SiemensPLCS
    from snap7.util import get_int, get_real, get_dword, get_string, get_byte, get_word, get_bool
    from fastapi import FastAPI
    import uvicorn
    from server import app, connect_plc
    import config

    if config.plcForwarderUrl:
        connect_plc(config.plcForwarderUrl, config.plcForwarderRack, config.plcForwarderSlot)
        # from server import forward_request
        # c=forward_request("DB26.2","word", 2)
        # print(c)
    uvicorn.run(app=app, host=config.server_ip, port=config.server_port)
