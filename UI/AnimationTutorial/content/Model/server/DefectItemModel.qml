import QtQuick

Item {
    id:root
    property int id_
    property int coilId
    property string surface
    property int defectClass
    property string defectName:""
    property int defectStatus
    property int defectX
    property int defectY
    property int defectW
    property int defectH
    property real defectSource
    property var defectData
    property int defectLevel:global.defectClassProperty.getDefectLevelByDefectName(defectName)
    property color defectColor:global.defectClassProperty.getColorByName(defectName)

    // defectTime = Column(DateTime, server_default=func.now())

    function init(item){
            id_ = item.Id
            coilId = item.secondaryCoilId
            surface = item.surface
            defectClass = item.defectClass
            defectName = item.defectName
            defectStatus = item.defectStatus
            defectX = item.defectX
            defectY = item.defectY
            defectW = item.defectW
            defectH = item.defectH
            defectSource = item.defectSource
            defectData = item.defectData
    }

    property string defect_url:api.get_defect_url(
                                   surface,
                                   coilId,
                                   defectName,
                                   defectX,
                                   defectY,
                                   defectW,
                                   defectH
                                   )
}
