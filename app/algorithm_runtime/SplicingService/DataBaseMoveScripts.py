

from CoilDataBase.Alarm import Session
from CoilDataBase.models.Coil import Coil
from CoilDataBase.models.SecondaryCoil import SecondaryCoil

with Session() as session:
    print(session.query(SecondaryCoil).first().Id)
