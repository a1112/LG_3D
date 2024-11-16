from CoilDataBase.Coil import getAllJoinQuery
from CoilDataBase.core import Session
from CoilDataBase.models import SecondaryCoil, Coil

if __name__=="__main__":
    from sqlalchemy.orm import joinedload, selectinload

    session=Session()
    # 示例：查询 SecondaryCoil，同时预加载多个子表的数据
    results = (
        getAllJoinQuery(session)
        [:10]
    )

    # 输出查询结果
    for coil in results:
        print("SecondaryCoil:", coil.Id)
        print("childrenCoil:", coil.childrenCoil)
        print("childrenAlarmFlatRoll:", coil.childrenAlarmFlatRoll)
        print("childrenTaperShapePoint:", coil.childrenTaperShapePoint)
        print("childrenAlarmInfo:", coil.childrenAlarmInfo)
        print("childrenAlarmTaperShape:", coil.childrenAlarmTaperShape)
        print("childrenDetectionSpeed:", coil.childrenDetectionSpeed)


