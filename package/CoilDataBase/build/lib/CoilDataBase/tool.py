import datetime

from .models import *
from .core import Session


def get_date_info(date_time):
    """
    将时间戳，datetime，转换成 字典
    :param date_time:
    :return:
    """
    if isinstance(date_time, datetime.datetime):
        return {"year": date_time.year,
                "month": date_time.month,
                "weekday": date_time.weekday(),
                "day": date_time.day,
                "hour": date_time.hour,
                "minute": date_time.minute,
                "second": date_time.second,
                }
    if isinstance(date_time, (float, int)):
        return get_date_info(datetime.datetime.fromtimestamp(date_time))
    if isinstance(date_time, datetime.timedelta):
        return {"day": date_time.days,
                "hour": int(date_time.seconds / 3600),
                "minute": int(date_time.seconds / 60) % 60,
                "second": date_time.seconds % 60
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
        return get_date_info(obj)
    else:
        return obj


def clear_by_coil_id(coil_id):
    """
        数据清理
    Args:
        coil_id:

    Returns:
    """
    with Session() as session:
        session.query(Coil).filter(Coil.SecondaryCoilId == coil_id).delete()
        session.query(CoilState).filter(CoilState.secondaryCoilId == coil_id).delete()
        session.query(CoilAlarmStatus).filter(CoilAlarmStatus.secondaryCoilId == coil_id).delete()
        session.query(AlarmFlatRoll).filter(AlarmFlatRoll.secondaryCoilId == coil_id).delete()
        session.query(TaperShapePoint).filter(TaperShapePoint.secondaryCoilId == coil_id).delete()
        session.query(AlarmTaperShape).filter(AlarmTaperShape.secondaryCoilId == coil_id).delete()
        session.query(AlarmLooseCoil).filter(AlarmLooseCoil.secondaryCoilId == coil_id).delete()
        session.query(AlarmInfo).filter(AlarmInfo.secondaryCoilId == coil_id).delete()
        session.query(ServerDetectionError).filter(ServerDetectionError.secondaryCoilId == coil_id).delete()
        session.query(DataEllipse).filter(DataEllipse.secondaryCoilId == coil_id).delete()
        session.query(LineData).filter(LineData.secondaryCoilId == coil_id).delete()
        session.query(PointData).filter(PointData.secondaryCoilId == coil_id).delete()
        session.query(CoilDefect).filter(CoilDefect.secondaryCoilId == coil_id).delete()
        session.commit()

def add_obj(obj):
    """
    添加数据
    """
    with Session() as session:
        if isinstance(obj, list):
            session.add_all(obj)
            # [session.add(o) for o in obj]
        else:
            session.add(obj)
        # session.flush()
        session.commit()