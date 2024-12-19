from . import tool
from .core import Session
from .models import *


def addObj(obj):
    return tool.addObj(obj)


def addAlarmFlatRoll(alarmFlatRoll):
    return addObj(alarmFlatRoll)


def getAlarmFlatRoll(coilId):
    with Session() as session:
        return session.query(AlarmFlatRoll).where(coilId == AlarmFlatRoll.secondaryCoilId)[:2]


def addAlarmTaperShape(alarmTaperShape):
    return addObj(alarmTaperShape)


def addAlarmLooseCoil(alarmLooseCoil):
    return addObj(alarmLooseCoil)


def getAlarmTaperShape(coilId):
    with Session() as session:
        return session.query(AlarmTaperShape).where(coilId == AlarmTaperShape.secondaryCoilId)


def getAlarmLooseCoil(coilId):
    with Session() as session:
        return session.query(AlarmLooseCoil).where(AlarmLooseCoil.secondaryCoilId == coilId).all()
