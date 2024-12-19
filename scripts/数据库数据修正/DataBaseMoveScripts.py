

from CoilDataBase.Alarm import Session
from CoilDataBase.models.SecondaryCoil import SecondaryCoil

with Session() as session:
    old_secondaryCoil = None
    for secondaryCoil in session.query(SecondaryCoil).where(SecondaryCoil.CreateTime < "2024-12-09 21:00:00"):
        if old_secondaryCoil:
            if old_secondaryCoil.CoilNo==secondaryCoil.CoilNo:
                print(secondaryCoil.Id,secondaryCoil.CoilNo,secondaryCoil.CreateTime)
        old_secondaryCoil = secondaryCoil
    #     if old_secondaryCoil:
    #         old_secondaryCoil.CoilNo = secondaryCoil.CoilNo
    #         old_secondaryCoil.CoilType = secondaryCoil.CoilType
    #         old_secondaryCoil.CoilInside = old_secondaryCoil.CoilInside
    #         old_secondaryCoil.CoilDia = secondaryCoil.CoilDia
    #         old_secondaryCoil.Thickness = secondaryCoil.Thickness
    #         old_secondaryCoil.Width = secondaryCoil.Width
    #         old_secondaryCoil.Weight = secondaryCoil.Weight
    #         old_secondaryCoil.ActWidth = secondaryCoil.ActWidth
    #         old_secondaryCoil.CreateTime = secondaryCoil.CreateTime
    #     old_secondaryCoil = secondaryCoil
    # session.commit()
