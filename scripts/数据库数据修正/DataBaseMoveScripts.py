

from CoilDataBase.Alarm import Session
from CoilDataBase.models import Coil, SecondaryCoil

with Session() as session:
    print(session.query(SecondaryCoil).first().Id)
    old_secondaryCoil = None
    for secondaryCoil in session.query(SecondaryCoil):

        if old_secondaryCoil:
            old_secondaryCoil.CoilNo=secondaryCoil.CoilNo
            old_secondaryCoil.CoilType=secondaryCoil.CoilType
            old_secondaryCoil.CoilInside=old_secondaryCoil.CoilInside
            old_secondaryCoil.CoilDia=secondaryCoil.CoilDia
            old_secondaryCoil.Thickness=secondaryCoil.Thickness
            old_secondaryCoil.Width=secondaryCoil.Width
            old_secondaryCoil.Weight=secondaryCoil.Weight
            old_secondaryCoil.ActWidth=secondaryCoil.ActWidth
            old_secondaryCoil.CreateTime=secondaryCoil.CreateTime
        old_secondaryCoil=secondaryCoil
    session.commit()