from .models import *
from .core import Session

def addAlarmFlatRoll(alarmFlatRoll):
    with Session() as session:
        session.add(alarmFlatRoll)
        session.commit()


def getAlarmFlatRoll(coilId):
    with Session() as session:
        return session.query(AlarmFlatRoll).where(coilId==AlarmFlatRoll.secondaryCoilId)[:2]

def addAlarmTaperShape(alarmTaperShape):
    with Session() as session:
        session.add(alarmTaperShape)
        session.commit()

def addAlarmLooseCoil(alarmLooseCoil):
    with Session() as session:
        session.add(alarmLooseCoil)
        session.commit()

def getAlarmTaperShape(coilId):
    with Session() as session:
        return session.query(AlarmTaperShape).where(coilId==AlarmTaperShape.secondaryCoilId)

def getAlarmLooseCoil(coilId):
    with Session() as session:
        return session.query(AlarmLooseCoil).where(AlarmLooseCoil.secondaryCoilId==coilId).all()
