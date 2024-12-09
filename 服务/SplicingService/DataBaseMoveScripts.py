

from CoilDataBase.Alarm import Session
from CoilDataBase.models import Coil, SecondaryCoil

with Session() as session:
    print(session.query(SecondaryCoil).first().Id)
