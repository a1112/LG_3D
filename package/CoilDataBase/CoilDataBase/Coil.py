import datetime
from typing import List

from sqlalchemy.orm import subqueryload

from . import tool
from .core import Session
from .models import *


def addObj(obj):
    return tool.add_obj(obj)


def getAllJoinQuery(session: Session):
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


def getAllJoinDataByNum(num, maxsize=None):
    with Session() as session:
        if maxsize:
            return getAllJoinQuery(session).filter(SecondaryCoil.Id < maxsize).order_by(SecondaryCoil.Id.desc())[:num]
        return getAllJoinQuery(session).order_by(SecondaryCoil.Id.desc())[:num]


def getAllJoinDataByTime(startTime, endTime):
    with Session() as session:
        return getAllJoinQuery(session).filter(SecondaryCoil.CreateTime >= startTime,
                                               SecondaryCoil.CreateTime <= endTime).order_by(
            SecondaryCoil.Id.desc()).all()


def get_join_query(session: Session, by_coil = True):
    """
        运行较慢
    """
    query = session.query(SecondaryCoil).options(subqueryload(SecondaryCoil.childrenAlarmInfo),
                                                 subqueryload(SecondaryCoil.childrenCoil))
    if by_coil:
        last_coil = session.query(Coil).order_by(Coil.Id.desc()).first()
        query = query.filter(SecondaryCoil.Id <= last_coil.SecondaryCoilId)
    return query


def addSecondaryCoil(coil: SecondaryCoil):
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


def getSecondaryCoil(num: int, desc=True) -> List[SecondaryCoil]:
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


def deleteDefectsBySecondaryCoilId(secondaryCoilId, surface):
    """
        移除检测数据
    Args:
        secondaryCoilId:
        surface:

    Returns:

    """
    with Session() as session:
        session.query(CoilDefect).filter(CoilDefect.secondaryCoilId == secondaryCoilId and
                                         surface == CoilDefect.surface).delete()
        session.commit()


def addDefects(defects: List[dict]):
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


def getSecondaryCoilById(id_):
    with Session() as session:
        return session.query(SecondaryCoil).where(SecondaryCoil.Id > id_)


def getCoil(num):
    with Session() as session:
        return session.query(Coil).order_by(Coil.Id.desc())[:num]


def deleteCoil(id_):
    print(f"数据删除 {id_}")
    with Session() as session:
        session.query(Coil).filter(Coil.SecondaryCoilId > id_).delete()
        session.commit()


def getCoilList(num, coil_id=None, by_coil=True):
    with (Session() as session):
        query = get_join_query(session, by_coil=by_coil)

        if coil_id:
            query = query.filter(SecondaryCoil.Id > coil_id)
        return query.order_by(SecondaryCoil.Id.desc())[:num]


def searchByCoilNo(coilNo):
    with Session() as session:
        query = get_join_query(session)
        return query.filter(SecondaryCoil.CoilNo.like(f"%{coilNo}%")).all()


def getIdlistByCoilNo(coilNo, endCoilNo):
    with Session() as session:
        return session.query(SecondaryCoil.Id).filter(SecondaryCoil.CoilNo >= coilNo,
                                                      SecondaryCoil.CoilNo <= endCoilNo).all()


def searchByCoilId(coilId, endCoilId=None):
    with Session() as session:
        query = get_join_query(session)
        if endCoilId:
            return query.filter(SecondaryCoil.Id >= coilId, SecondaryCoil.Id <= endCoilId).all()
        return query.filter(SecondaryCoil.Id == coilId).all()


def searchByDateTime(startTime, endTimeq):
    with Session() as session:
        query = get_join_query(session)
        return query.filter(SecondaryCoil.CreateTime >= startTime, SecondaryCoil.CreateTime <= endTimeq).all()


def addCoilState(coilState):
    with Session() as session:
        session.add(coilState)
        session.commit()


def getCoilState(coilId):
    with Session() as session:
        return session.query(CoilState).filter(CoilState.secondaryCoilId == coilId).order_by(CoilState.Id.desc())[:2]


def getPlcData(coilId):
    with Session() as session:
        return session.query(PlcData).filter(PlcData.secondaryCoilId == coilId).order_by(PlcData.Id.desc()).first()


def getDefects(coilId, direction):
    with Session() as session:
        return session.query(CoilDefect).filter(CoilDefect.secondaryCoilId == coilId,
                                                CoilDefect.surface == direction).all()


def getDefetClassDict():
    with Session() as session:
        return session.query(DefectClassDict).all()


def getCoilByCoilNo(coilNo):
    with Session() as session:
        return session.query(SecondaryCoil).filter(SecondaryCoil.CoilNo == coilNo).first()


def addToPlc(coilDdata):
    with Session() as session:
        session.add(PlcData(
            secondaryCoilId=coilDdata["secondaryCoilId"],
            location_S=coilDdata["location_S"],
            location_L=coilDdata["location_L"],
            location_laser=coilDdata["location_laser"],
            startTime=datetime.datetime.now(),
        ))
        session.commit()


def deleteCoilByCoilId(Id_):
    with Session() as session:
        session.query(Coil).filter(Coil.SecondaryCoilId > Id_).delete()
        session.commit()


def getCoilStateByCoilId(coil_id, surface):
    with Session() as session:
        return session.query(CoilState).filter(CoilState.secondaryCoilId == coil_id,
                                               CoilState.surface == surface).order_by(CoilState.Id.desc()).first()


def addServerDetectionError(error: ServerDetectionError):
    return addObj(error)


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


def get_point_data(coil_id, surfaceKey=None):
    with Session() as session:
        que = session.query(PointData).filter(PointData.secondaryCoilId == coil_id)
        if surfaceKey:
            que = que.filter(PointData.surface == surfaceKey)
        return que.all()


def get_line_data(coil_id, surfaceKey=None):
    with Session() as session:
        que = session.query(LineData).filter(LineData.secondaryCoilId == coil_id)
        if surfaceKey:
            que = que.filter(LineData.surface == surfaceKey)
        return que.all()
