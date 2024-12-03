from .models import *
from .core import Session

def addObj(obj):
    with Session() as session:
        if isinstance(obj,list):
            session.add_all(obj)
            # [session.add(o) for o in obj]
        else:
            session.add(obj)
        session.flush()
        # session.commit()

def addAlarmFlatRoll(alarmFlatRoll):
    return addObj(alarmFlatRoll)


def getAlarmFlatRoll(coilId):
    with Session() as session:
        return session.query(AlarmFlatRoll).where(coilId==AlarmFlatRoll.secondaryCoilId)[:2]

def addAlarmTaperShape(alarmTaperShape):
    return addObj(alarmTaperShape)

def addAlarmLooseCoil(alarmLooseCoil):
    return addObj(alarmLooseCoil)

def getAlarmTaperShape(coilId):
    with Session() as session:
        return session.query(AlarmTaperShape).where(coilId==AlarmTaperShape.secondaryCoilId)

def getAlarmLooseCoil(coilId):
    with Session() as session:
        return session.query(AlarmLooseCoil).where(AlarmLooseCoil.secondaryCoilId==coilId).all()
