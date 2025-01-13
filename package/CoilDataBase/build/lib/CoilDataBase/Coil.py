import datetime
from typing import List

from sqlalchemy.orm import subqueryload

from . import tool
from .core import Session
from .models import *


def add_obj(obj):
    return tool.add_obj(obj)


def get_all_join_query(session: Session):
    return session.query(SecondaryCoil) \
        .options(
        subqueryload(SecondaryCoil.childrenCoil),
        subqueryload(SecondaryCoil.childrenCoilState),
        subqueryload(SecondaryCoil.childrenCoilDefect),
        subqueryload(SecondaryCoil.childrenCoilAlarmStatus),
        subqueryload(SecondaryCoil.childrenAlarmFlatRoll),
        subqueryload(SecondaryCoil.childrenTaperShapePoint),
        subqueryload(SecondaryCoil.childrenAlarmInfo),
        subqueryload(SecondaryCoil.childrenPlcData),
        subqueryload(SecondaryCoil.childrenAlarmTaperShape),
        subqueryload(SecondaryCoil.childrenAlarmLooseCoil),
        subqueryload(SecondaryCoil.childrenDetectionSpeed),
        subqueryload(SecondaryCoil.childrenServerDetectionError),
    )


def get_all_join_data_by_id(start_id,end_id):
    with Session() as session:
        return get_all_join_query(session).filter(SecondaryCoil.Id >= start_id,
                                                  SecondaryCoil.Id <= end_id).order_by(SecondaryCoil.Id.desc()).all()


def get_all_join_data_by_num(num, maxsize=None):
    with Session() as session:
        if maxsize:
            return get_all_join_query(session).filter(SecondaryCoil.Id < maxsize).order_by(SecondaryCoil.Id.desc())[:num]
        return get_all_join_query(session).order_by(SecondaryCoil.Id.desc())[:num]


def get_all_join_data_by_time(start_time, end_time):
    with Session() as session:
        return get_all_join_query(session).filter(SecondaryCoil.CreateTime >= start_time,
                                                  SecondaryCoil.CreateTime <= end_time).order_by(
            SecondaryCoil.Id.desc()).all()


def get_join_query(session: Session, by_coil = True):
    """
        查询的返回数据
    Args:
        session: Session
        by_coil:
    """
    query = session.query(SecondaryCoil).options(subqueryload(SecondaryCoil.childrenAlarmInfo), # 塔形报警
                                                 subqueryload(SecondaryCoil.childrenCoil),       # 二级数据
                                                 subqueryload(SecondaryCoil.childrenCoilDefect)  # 缺陷数据
                                                 )
    if by_coil:
        last_coil = session.query(Coil).order_by(Coil.Id.desc()).first()
        query = query.filter(SecondaryCoil.Id <= last_coil.SecondaryCoilId)
    return query


def add_secondary_coil(coil: SecondaryCoil):
    """
        添加二级数据
    Args:
        coil:

    Returns:

    """
    with Session() as session:
        session.add(SecondaryCoil(
            CoilNo=coil["Coil_ID"],
            CoilType=coil["Steel_Grade"],
            CoilInside=coil["coil_in_dia"],
            CoilDia=coil["coil_dia"],
            Thickness=coil["FM_Tar_Thickness"],
            Width=coil["FM_Tar_Width"],
            Weight=coil["sp01"][0],
            ActWidth=coil["act_w"],
            CreateTime=datetime.datetime.now()
        ))
        session.commit()


def get_secondary_coil(num: int, desc=True) -> List[SecondaryCoil]:
    """
        获取二级数据
    Args:
        num:    数量
        desc:   是否倒序

    Returns:

    """
    with Session() as session:
        if desc:
            return session.query(SecondaryCoil).order_by(SecondaryCoil.Id.desc())[:num]
        else:
            return session.query(SecondaryCoil).order_by(SecondaryCoil.Id.asc())[:num]


def addCoil(coil):
    """
        添加检测数据
    Args:
        coil:

    Returns:

    """
    with Session() as session:
        session.add(Coil(
            SecondaryCoilId=coil["SecondaryCoilId"],
            DetectionTime=datetime.datetime.now(),
            DefectCountS=coil["DefectCountS"],
            DefectCountL=coil["DefectCountL"],
            CheckStatus=coil["CheckStatus"],
            Status_L=coil["Status_L"],
            Status_S=coil["Status_S"],
            Grade=coil["Grade"],
            Msg=coil["Msg"]
        ))
        session.commit()


def deleteDefectsBySecondaryCoilId(secondary_coil_id, surface):
    """
        移除检测数据
    Args:
        secondary_coil_id:
        surface:

    Returns:

    """
    with Session() as session:
        session.query(CoilDefect).filter(CoilDefect.secondaryCoilId == secondary_coil_id and
                                         surface == CoilDefect.surface).delete()
        session.commit()


def add_defects(defects: List[dict]):
    """
        增加缺陷数据
    Args:
        defects:

    Returns:

    """
    with Session() as session:
        session.add_all([CoilDefect(
            secondaryCoilId=defect["secondaryCoilId"],
            surface=defect["surface"],
            defectClass=defect["defectClass"],
            defectName=defect["defectName"],
            defectStatus=defect["defectStatus"],
            defectTime=datetime.datetime.now(),
            defectX=defect["defectX"],
            defectY=defect["defectY"],
            defectW=defect["defectW"],
            defectH=defect["defectH"],
            defectSource=defect["defectSource"],
            defectData=defect["defectData"],
        ) for defect in defects])
        session.commit()


def get_secondary_coil_by_id(id_):
    with Session() as session:
        return session.query(SecondaryCoil).where(SecondaryCoil.Id > id_)


def get_coil(num):
    with Session() as session:
        return session.query(Coil).order_by(Coil.Id.desc())[:num]


def delete_coil(id_):
    print(f"数据删除 {id_}")
    with Session() as session:
        session.query(Coil).filter(Coil.SecondaryCoilId > id_).delete()
        session.commit()


def get_coil_list(num, coil_id=None, by_coil=True):
    with (Session() as session):
        query = get_join_query(session, by_coil=by_coil)

        if coil_id:
            query = query.filter(SecondaryCoil.Id > coil_id)
        return query.order_by(SecondaryCoil.Id.desc())[:num]


def search_by_coil_no(coil_no):
    with Session() as session:
        query = get_join_query(session)
        return query.filter(SecondaryCoil.CoilNo.like(f"%{coil_no}%")).all()


def get_idlist_by_coil_no(coil_no, end_coil_no):
    with Session() as session:
        return session.query(SecondaryCoil.Id).filter(SecondaryCoil.CoilNo >= coil_no,
                                                      SecondaryCoil.CoilNo <= end_coil_no).all()


def searchByCoilId(coil_id, end_coil_id = None):
    with Session() as session:
        query = get_join_query(session)
        if end_coil_id:
            return query.filter(SecondaryCoil.Id >= coil_id, SecondaryCoil.Id <= end_coil_id).all()
        return query.filter(SecondaryCoil.Id == coil_id).all()


def searchByDateTime(start_time, end_timeq):
    with Session() as session:
        query = get_join_query(session)
        return query.filter(SecondaryCoil.CreateTime >= start_time, SecondaryCoil.CreateTime <= end_timeq).all()


def addCoilState(coil_state):
    with Session() as session:
        session.add(coil_state)
        session.commit()


def getCoilState(coil_id):
    with Session() as session:
        return session.query(CoilState).filter(CoilState.secondaryCoilId == coil_id).order_by(CoilState.Id.desc())[:2]


def get_plc_data(coil_id):
    with Session() as session:
        return session.query(PlcData).filter(PlcData.secondaryCoilId == coil_id).order_by(PlcData.Id.desc()).first()

def get_all_defects(coil_id):
    with Session() as session:
        return session.query(CoilDefect).filter(CoilDefect.secondaryCoilId == coil_id).all()

def get_defects(coil_id, direction):
    with Session() as session:
        return session.query(CoilDefect).filter(CoilDefect.secondaryCoilId == coil_id,
                                                CoilDefect.surface == direction).all()


def get_defect_class_dict():
    with Session() as session:
        return session.query(DefectClassDict).all()


def get_coil_by_coil_no(coil_no):
    with Session() as session:
        return session.query(SecondaryCoil).filter(SecondaryCoil.CoilNo == coil_no).first()


def addToPlc(coil_ddata):
    with Session() as session:
        session.add(PlcData(
            secondaryCoilId=coil_ddata["secondaryCoilId"],
            location_S=coil_ddata["location_S"],
            location_L=coil_ddata["location_L"],
            location_laser=coil_ddata["location_laser"],
            startTime=datetime.datetime.now(),
        ))
        session.commit()


def deleteCoilByCoilId(Id_):
    with Session() as session:
        session.query(Coil).filter(Coil.SecondaryCoilId > Id_).delete()
        session.commit()


def get_coil_state_by_coil_id(coil_id, surface):
    with Session() as session:
        return session.query(CoilState).filter(CoilState.secondaryCoilId == coil_id,
                                               CoilState.surface == surface).order_by(CoilState.Id.desc()).first()


def add_server_detection_error(error: ServerDetectionError):
    return add_obj(error)


def add_coil(coil):
    with Session() as session:
        session.add(SecondaryCoil(
            CoilNo=coil["Coil_ID"],
            CoilType=coil["Steel_Grade"],
            CoilInside=coil["coil_in_dia"],
            CoilDia=coil["coil_dia"],
            Thickness=coil["FM_Tar_Thickness"],
            Width=coil["FM_Tar_Width"],
            Weight=coil["sp01"][0],
            ActWidth=coil["act_w"],
            CreateTime=datetime.datetime.now()
        ))
        session.commit()


def get_last_coil():
    with Session() as session:
        return session.query(SecondaryCoil).order_by(SecondaryCoil.CreateTime.desc()).first()


def get_point_data(coil_id, surface_key=None):
    with Session() as session:
        que = session.query(PointData).filter(PointData.secondaryCoilId == coil_id)
        if surface_key:
            que = que.filter(PointData.surface == surface_key)
        return que.all()


def get_line_data(coil_id, surface_key=None):
    with Session() as session:
        que = session.query(LineData).filter(LineData.secondaryCoilId == coil_id)
        if surface_key:
            que = que.filter(LineData.surface == surface_key)
        return que.all()
