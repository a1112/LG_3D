from CoilDataBase import config
config.Config.host="192.168.99.100"
from CoilDataBase.Coil import getAllJoinQuery
from CoilDataBase.core import Session

if __name__=="__main__":

    from CoilDataBase.backup import backup_to_sqlite

    backup_to_sqlite("test.db")


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


