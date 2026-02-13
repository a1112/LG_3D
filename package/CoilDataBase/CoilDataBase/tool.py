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
    return date_time

def to_dict(obj, up_data: dict = None, _depth=0, _max_depth=10):
    """
    转换成可序列化的字典
    处理 SQLAlchemy relationship 属性

    Args:
        obj: 要转换的对象
        up_data: 更新的数据字典
        _depth: 当前递归深度（内部使用）
        _max_depth: 最大递归深度（防止循环引用）
    """
    # 防止无限递归
    if _depth >= _max_depth:
        return str(obj)

    if isinstance(obj, list):
        return [to_dict(i, None, _depth + 1, _max_depth) for i in obj]

    # 处理 SQLAlchemy 对象
    if hasattr(obj, "__dict__") and "_sa_instance_state" in obj.__dict__:
        if not up_data:
            up_data = {}

        # 只获取实例属性（列），排除 relationship 和内部属性
        for key, value in obj.__dict__.items():
            if key.startswith('_'):
                continue
            # 跳过 SQLAlchemy 内部状态
            if key == '_sa_instance_state':
                continue
            # 跳过 relationship 属性（避免循环引用）
            if hasattr(value, '__iter__') and not isinstance(value, (str, bytes, bytearray)):
                # 如果是集合类型，尝试转换为列表
                try:
                    # 检查是否是 SQLAlchemy 集合
                    if hasattr(value, 'all'):
                        # 是 InstrumentedList，转换为列表递归处理
                        up_data[key] = [to_dict(item, None, _depth + 1, _max_depth) for item in value]
                    else:
                        # 其他可迭代对象
                        up_data[key] = value
                except Exception:
                    up_data[key] = value
            elif isinstance(value, datetime.datetime):
                up_data[key] = get_date_info(value)
            else:
                up_data[key] = value

        rd = {}
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
