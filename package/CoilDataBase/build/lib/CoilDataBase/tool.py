import datetime

from . import models
from .core import Session


def getDateInfo(dateTime):
    """
    将时间戳，datetime，转换成 字典
    :param dateTime:
    :return:
    """
    if isinstance(dateTime, datetime.datetime):
        return {"year": dateTime.year,
                "month": dateTime.month,
                "weekday": dateTime.weekday(),
                "day": dateTime.day,
                "hour": dateTime.hour,
                "minute": dateTime.minute,
                "second": dateTime.second,
                }
    if isinstance(dateTime, (float, int)):
        return getDateInfo(datetime.datetime.fromtimestamp(dateTime))
    if isinstance(dateTime, datetime.timedelta):
        return {"day": dateTime.days,
                "hour": int(dateTime.seconds / 3600),
                "minute": int(dateTime.seconds / 60) % 60,
                "second": dateTime.seconds % 60
                }


def to_dict(obj, up_data: dict = None):
    """
    转换成可序列化的字典
    """
    if isinstance(obj, list):
        return [to_dict(i) for i in obj]
    if hasattr(obj, "__dict__") and "_sa_instance_state" in obj.__dict__:
        if not up_data:
            up_data = {}
        if len(obj.__dict__) <= 1:
            rd = {key: to_dict(getattr(obj, key)) for key in obj.__dir__() if not key.startswith('_')
                  and key not in ["metadata"] and key not in up_data}
        else:
            rd = {key: to_dict(getattr(obj, key)) for key in obj.__dict__ if
                  key not in ["_sa_instance_state"] and key not in up_data}
        rd.update(up_data)
        return rd
    elif isinstance(obj, datetime.datetime):
        return getDateInfo(obj)
    else:
        return obj


def clear_by_coil_id(coilId):
    """
        数据清理
    Args:
        coilId:

    Returns:
    """
    with Session() as session:
        session.query(models.Coil).filter(models.Coil.SecondaryCoilId == coilId).delete()
        session.query(models.CoilState).filter(models.CoilState.secondaryCoilId == coilId).delete()
        session.query(models.CoilAlarmStatus).filter(models.CoilAlarmStatus.secondaryCoilId == coilId).delete()
        session.query(models.AlarmFlatRoll).filter(models.AlarmFlatRoll.secondaryCoilId == coilId).delete()
        session.query(models.TaperShapePoint).filter(models.TaperShapePoint.secondaryCoilId == coilId).delete()
        session.query(models.AlarmTaperShape).filter(models.AlarmTaperShape.secondaryCoilId == coilId).delete()
        session.query(models.AlarmLooseCoil).filter(models.AlarmLooseCoil.secondaryCoilId == coilId).delete()
        session.query(models.AlarmInfo).filter(models.AlarmInfo.secondaryCoilId == coilId).delete()
        session.query(models.ServerDetectionError).filter(models.ServerDetectionError.secondaryCoilId == coilId).delete()
        session.query(models.DataEllipse).filter(models.DataEllipse.secondaryCoilId == coilId).delete()
        session.query(models.LineData).filter(models.LineData.secondaryCoilId == coilId).delete()
        session.query(models.PointData).filter(models.PointData.secondaryCoilId == coilId).delete()
        session.query(models.CoilDefect).filter(models.CoilDefect.secondaryCoilId == coilId).delete()
        session.commit()

def addObj(obj):
    with Session() as session:
        if isinstance(obj, list):
            session.add_all(obj)
            # [session.add(o) for o in obj]
        else:
            session.add(obj)
        # session.flush()
        session.commit()