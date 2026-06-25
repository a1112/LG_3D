import datetime

from CoilDataBase.core import Session
from CoilDataBase.models import SecondaryCoil


def add_coil(coil):
    with Session() as session:
        session.add(SecondaryCoil(
            CoilNo=coil["Coil_ID"],
            CoilType=coil["Steel_Grade"],
            CoilInside=coil["coil_in_dia"],
            CoilDia=coil["coil_dia"],
            Thickness=coil["FM_Tar_Thickness"],
            Width=coil["FM_Tar_Width"],
            ActWidth=coil["act_w"],
            Weight=ord(coil["outCode"]),
            CreateTime=datetime.datetime.now(),
        ))
        session.commit()
