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


def get_all_join_data_by_id(start_id, end_id):
    with Session() as session:
        return get_all_join_query(session).filter(SecondaryCoil.Id >= start_id,
                                                  SecondaryCoil.Id <= end_id).order_by(SecondaryCoil.Id.desc()).all()


def get_all_join_data_by_num(num, maxsize=None):
    with Session() as session:
        if maxsize:
            return get_all_join_query(session).filter(SecondaryCoil.Id < maxsize).order_by(SecondaryCoil.Id.desc())[
                   :num]
        return get_all_join_query(session).order_by(SecondaryCoil.Id.desc())[:num]


def get_all_join_data_by_time(start_time, end_time):
    with Session() as session:
        return get_all_join_query(session).filter(SecondaryCoil.CreateTime >= start_time,
                                                  SecondaryCoil.CreateTime <= end_time).order_by(
            SecondaryCoil.Id.desc()).all()


def get_join_query(session: Session, by_coil=True):
    """
        查询的返回数据
    Args:
        session: Session
        by_coil:
    """
    query = session.query(SecondaryCoil).options(subqueryload(SecondaryCoil.childrenAlarmInfo),  # 塔形报警
                                                 subqueryload(SecondaryCoil.childrenCoil),  # 二级数据
                                                 subqueryload(SecondaryCoil.childrenCoilDefect),  # 缺陷数据
                                                 subqueryload(SecondaryCoil.childrenCoilCheck)  # 检测
                                                 )
    if by_coil:
        last_coil = session.query(Coil).order_by(Coil.Id.desc()).first()
        query = query.filter(SecondaryCoil.Id <= last_coil.SecondaryCoilId)
    return query

def get_grad_query(session):
    query = session.query(SecondaryCoil).options(
                                                 subqueryload(SecondaryCoil.childrenCoil),  # 二级数据
                                                 ).order_by(SecondaryCoil.Id.desc())
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
    添加检测数据（去重：如果已存在则更新）
    Args:
        coil:

    Returns:

    """
    with Session() as session:
        secondary_coil_id = coil["SecondaryCoilId"]

        # 查询是否已存在该 secondary_coil_id 的记录
        existing = session.query(Coil).filter_by(SecondaryCoilId=secondary_coil_id).first()

        if existing:
            # 已存在，更新记录
            existing.DetectionTime = datetime.datetime.now()
            existing.DefectCountS = coil.get("DefectCountS", 0)
            existing.DefectCountL = coil.get("DefectCountL", 0)
            existing.CheckStatus = coil.get("CheckStatus", 0)
            existing.Status_L = coil.get("Status_L", 0)
            existing.Status_S = coil.get("Status_S", 0)
            existing.Grade = coil.get("Grade", 0)
            existing.Msg = coil.get("Msg", "")
        else:
            # 不存在，新增记录
            session.add(Coil(
                SecondaryCoilId=secondary_coil_id,
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
        return existing if existing else session.query(Coil).filter_by(SecondaryCoilId=secondary_coil_id).first()


def delete_defects_by_secondary_coil_id(secondary_coil_id, surface):
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
    if len(defects):
        print(fr"add_defects = {defects}")
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
    with Session() as session:
        query = get_join_query(session, by_coil=by_coil)
        if coil_id:
            query = query.filter(SecondaryCoil.Id > coil_id)
        return query.order_by(SecondaryCoil.Id.desc())[:num]


def get_grad_list(num):
    with Session() as session:
        query = get_grad_query(session)
        print(query.count())
        return query[:num]

def search_by_coil_no(coil_no):
    with Session() as session:
        query = get_join_query(session)
        return query.filter(SecondaryCoil.CoilNo.like(f"%{coil_no}%")).all()


def get_idlist_by_coil_no(coil_no, end_coil_no):
    with Session() as session:
        return session.query(SecondaryCoil.Id).filter(SecondaryCoil.CoilNo >= coil_no,
                                                      SecondaryCoil.CoilNo <= end_coil_no).all()


def searchByCoilId(coil_id, end_coil_id=None):
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



def  get_defects_all(start_coil_id, end_coil_id):
    with  Session() as session:
        return session.query(CoilDefect).filter(CoilDefect.secondaryCoilId >= start_coil_id,
                                                CoilDefect.secondaryCoilId <= end_coil_id).all()

def defects():
    with  Session() as session:
        return session.query(CoilDefect)

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


def get_coil_status_by_coil_id(coil_id):
    with Session() as session:
        que = session.query(CoilCheck).filter(CoilCheck.secondaryCoilId == coil_id)
        return que.first()


def set_coil_status_by_data(coil_id, status, msg):
    with Session() as session:
        que = session.query(CoilCheck).filter(CoilCheck.secondaryCoilId == coil_id)
        coil_check = que.all()
        if coil_check:
            coil_check = coil_check[0]
            coil_check.status = status
            coil_check.msg = msg
        else:
            session.add(CoilCheck(
                secondaryCoilId=coil_id,
                status=status,
                msg=msg
            ))

        session.commit()

def get_coilState(coil_id, surface_key=None)->CoilState:
    with Session() as session:
        que = session.query(CoilState).filter(CoilState.secondaryCoilId == coil_id).filter(CoilState.surface == surface_key)
        all_data=que.all()
        if all_data:
            return all_data[0]
        else:
            return None

list_data_keys = {
    "二级内径": SecondaryCoil.CoilInside,
    "二级卷径": SecondaryCoil.CoilDia,
    "二级厚度": SecondaryCoil.Thickness,
    "宽度": SecondaryCoil.Width,
    "PLC位置信息": PlcData,
    "缺陷": CoilDefect,
    "距离平均": "",
    "识别速度": "",
    "生产间隔": ""
}


# ==================== 手动标注缺陷 CRUD 操作 ====================

def add_manual_defect(defect_data: dict):
    """
    添加手动标注的缺陷

    Args:
        defect_data: 缺陷数据字典，包含：
            - secondaryCoilId: 二级卷ID
            - surface: 表面标识（S/L）
            - defectName: 缺陷名称
            - defectX: X坐标
            - defectY: Y坐标
            - defectW: 宽度
            - defectH: 高度
            - remark: 备注（可选）
            - annotator: 标注人（可选）

    Returns:
        创建的 ManualDefect 对象
    """
    from .models import DefectClassDict

    with Session() as session:
        # 获取缺陷类别信息
        defect_class = 0
        defect_name = defect_data.get("defectName", "未知缺陷")
        defect_dict = session.query(DefectClassDict).filter(
            DefectClassDict.defectName == defect_name
        ).first()
        if defect_dict:
            defect_class = defect_dict.defectClass

        # 创建手动标注缺陷
        manual_defect = ManualDefect(
            secondaryCoilId=defect_data["secondaryCoilId"],
            surface=defect_data["surface"],
            defectClass=defect_class,
            defectName=defect_name,
            defectStatus=1,
            defectX=defect_data["defectX"],
            defectY=defect_data["defectY"],
            defectW=defect_data["defectW"],
            defectH=defect_data["defectH"],
            defectSource=0,
            defectData=defect_data.get("defectData", ""),
            remark=defect_data.get("remark", ""),
            annotator=defect_data.get("annotator", "系统用户")
        )
        session.add(manual_defect)
        session.commit()
        session.refresh(manual_defect)
        return manual_defect


def update_manual_defect(defect_id: int, defect_data: dict):
    """
    更新手动标注的缺陷

    Args:
        defect_id: 缺陷ID
        defect_data: 更新的数据字典

    Returns:
        更新后的 ManualDefect 对象，如果不存在返回 None
    """
    from .models import DefectClassDict

    with Session() as session:
        manual_defect = session.query(ManualDefect).filter(
            ManualDefect.Id == defect_id
        ).first()

        if not manual_defect:
            return None

        # 更新字段
        if "defectName" in defect_data:
            defect_name = defect_data["defectName"]
            defect_dict = session.query(DefectClassDict).filter(
                DefectClassDict.defectName == defect_name
            ).first()
            if defect_dict:
                manual_defect.defectClass = defect_dict.defectClass
            manual_defect.defectName = defect_name

        if "defectStatus" in defect_data:
            manual_defect.defectStatus = defect_data["defectStatus"]
        if "defectX" in defect_data:
            manual_defect.defectX = defect_data["defectX"]
        if "defectY" in defect_data:
            manual_defect.defectY = defect_data["defectY"]
        if "defectW" in defect_data:
            manual_defect.defectW = defect_data["defectW"]
        if "defectH" in defect_data:
            manual_defect.defectH = defect_data["defectH"]
        if "remark" in defect_data:
            manual_defect.remark = defect_data["remark"]
        if "annotator" in defect_data:
            manual_defect.annotator = defect_data["annotator"]

        session.commit()
        session.refresh(manual_defect)
        return manual_defect


def delete_manual_defect(defect_id: int):
    """
    删除手动标注的缺陷

    Args:
        defect_id: 缺陷ID

    Returns:
        是否删除成功
    """
    with Session() as session:
        manual_defect = session.query(ManualDefect).filter(
            ManualDefect.Id == defect_id
        ).first()

        if not manual_defect:
            return False

        session.delete(manual_defect)
        session.commit()
        return True


def get_manual_defects(coil_id: int, surface: str = None):
    """
    获取手动标注的缺陷列表

    Args:
        coil_id: 二级卷ID
        surface: 表面标识（可选）

    Returns:
        ManualDefect 列表
    """
    with Session() as session:
        query = session.query(ManualDefect).filter(
            ManualDefect.secondaryCoilId == coil_id
        )
        if surface:
            query = query.filter(ManualDefect.surface == surface)
        return query.all()


def get_all_defects_including_manual(coil_id: int, surface: str):
    """
    获取所有缺陷（包括自动检测和手动标注）

    Args:
        coil_id: 二级卷ID
        surface: 表面标识

    Returns:
        包含自动检测缺陷和手动标注缺陷的列表
    """
    with Session() as session:
        # 获取自动检测的缺陷
        auto_defects = session.query(CoilDefect).filter(
            CoilDefect.secondaryCoilId == coil_id,
            CoilDefect.surface == surface
        ).all()

        # 获取手动标注的缺陷
        manual_defects = session.query(ManualDefect).filter(
            ManualDefect.secondaryCoilId == coil_id,
            ManualDefect.surface == surface
        ).all()

        # 合并结果
        result = []
        for d in auto_defects:
            result.append({
                "Id": d.Id,
                "type": "auto",
                "secondaryCoilId": d.secondaryCoilId,
                "surface": d.surface,
                "defectClass": d.defectClass,
                "defectName": d.defectName,
                "defectStatus": d.defectStatus,
                "defectTime": d.defectTime.isoformat() if d.defectTime else None,
                "defectX": d.defectX,
                "defectY": d.defectY,
                "defectW": d.defectW,
                "defectH": d.defectH,
                "defectSource": d.defectSource,
                "defectData": d.defectData,
            })
        for d in manual_defects:
            result.append({
                "Id": d.Id,
                "type": "manual",
                "secondaryCoilId": d.secondaryCoilId,
                "surface": d.surface,
                "defectClass": d.defectClass,
                "defectName": d.defectName,
                "defectStatus": d.defectStatus,
                "defectTime": d.createTime.isoformat() if d.createTime else None,
                "defectX": d.defectX,
                "defectY": d.defectY,
                "defectW": d.defectW,
                "defectH": d.defectH,
                "defectSource": d.defectSource,
                "defectData": d.defectData,
                "remark": d.remark,
                "annotator": d.annotator,
            })

        return result
