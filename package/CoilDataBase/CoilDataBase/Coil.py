from typing import List

from sqlalchemy.orm import joinedload, subqueryload

from .core import Session
from .models import *
from .tool import to_dict

def getAllJoinQuery(session: Session):
    return  session.query(SecondaryCoil)\
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
                )

def  getAllJoinDataByNum(num,max=None):
    with Session() as session:
        if max:
            return getAllJoinQuery(session).filter(SecondaryCoil.Id<max).order_by(SecondaryCoil.Id.desc())[:num]
        return getAllJoinQuery(session).order_by(SecondaryCoil.Id.desc())[:num]

def getAllJoinDataByTime(startTime,endTime):
    with Session() as session:
        return getAllJoinQuery(session).filter(SecondaryCoil.CreateTime>=startTime , SecondaryCoil.CreateTime<=endTime).order_by(SecondaryCoil.Id.desc()).all()

def getJoinQuery(session: Session,byCoil=True):
    """
    对于联合数据的查询
    Args:
        session:

    Returns:

    """
    byCoil=True
    query = session.query(SecondaryCoil).options(subqueryload(SecondaryCoil.childrenAlarmInfo)).options(subqueryload(SecondaryCoil.childrenCoil))

    if byCoil:
        lastCoil = session.query(Coil).order_by(Coil.Id.desc()).first()
        query = query.filter(SecondaryCoil.Id <= lastCoil.SecondaryCoilId)
    return query
    # return session.query(SecondaryCoil)\
    #                         .join(Coil)\
    #                         .join(AlarmInfo).order_by(SecondaryCoil.Id.desc())


def addSecondaryCoil(coil:SecondaryCoil):
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


# Base.metadata.drop_all(engine, tables=[SecondaryCoil.__table__])

def addObj(obj):
    with Session() as session:
        session.add(obj)
        session.commit()

def getSecondaryCoil(num:int, desc=True)->List[SecondaryCoil]:
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


def deleteDefectsBySecondaryCoilId(secondaryCoilId,surface):
    """
        移除检测数据
    Args:
        secondaryCoilId:
        surface:

    Returns:

    """
    with Session() as session:
        session.query(CoilDefect).filter(CoilDefect.secondaryCoilId == secondaryCoilId and
                                         surface  == CoilDefect.surface).delete()
        session.commit()


def addDefects(defects:List[dict]):
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
    with Session() as session:
        session.query(Coil).filter(Coil.SecondaryCoilId > id_).delete()
        session.commit()


def getCoilList(num,coilId=None,byCoil=False):
    byCoil=True
    with (Session() as session):
        query = getJoinQuery(session,byCoil=byCoil)

        if coilId:
            query = query.filter(SecondaryCoil.Id > coilId)
        return query.order_by(SecondaryCoil.Id.desc())[:num]


def searchByCoilNo(coilNo):
    with Session() as session:
        query = getJoinQuery(session)
        return query.filter(SecondaryCoil.CoilNo.like(f"%{coilNo}%")).all()


def getIdlistByCoilNo(coilNo,endCoilNo):
    with Session() as session:
        return session.query(SecondaryCoil.Id).filter(SecondaryCoil.CoilNo >= coilNo,SecondaryCoil.CoilNo<=endCoilNo).all()

def searchByCoilId(coilId,endCoilId=None):

    with Session() as session:
        query = getJoinQuery(session)
        if endCoilId:
            return query.filter(SecondaryCoil.Id >= coilId,SecondaryCoil.Id<=endCoilId).all()
        return query.filter(SecondaryCoil.Id == coilId).all()

def searchByDateTime(startTime,endTimeq):
    with Session() as session:
        query = getJoinQuery(session)
        return query.filter(SecondaryCoil.CreateTime>=startTime , SecondaryCoil.CreateTime<=endTimeq).all()

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


def getDefects(coilId,direction):
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

def getCoilStateByCoilId(coilId,surface):
    with Session() as session:
        return session.query(CoilState).filter(CoilState.secondaryCoilId == coilId,
                                                    CoilState.surface == surface).order_by(CoilState.Id.desc()).first()


