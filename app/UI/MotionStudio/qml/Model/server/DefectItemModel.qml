import QtQuick

Item {
    id: root

    property int id_
    property int coilId
    property string surface
    property int defectClass
    property string defectName: ""
    property string configDefectName: ""
    property int defectStatus
    property int defectX
    property int defectY
    property int defectW
    property int defectH
    property real defectSource
    property var defectData
    property bool isArea: false

    property int apiDefectLevel: -1

    property int defectLevel: {
        if (apiDefectLevel >= 0) {
            return apiDefectLevel
        }
        if (configDefectName || defectName) {
            return global.defectClassProperty.getDefectLevelByDefectName(configDefectName || defectName)
        }
        return 0
    }

    property color defectColor: global.defectClassProperty.getColorByName(configDefectName || defectName)
    property string defect_url: ""

    function init(item) {
        id_ = 0
        coilId = 0
        surface = "S"
        defectClass = 0
        defectName = ""
        configDefectName = ""
        defectStatus = 0
        defectX = 0
        defectY = 0
        defectW = 0
        defectH = 0
        defectSource = 0
        defectData = undefined
        apiDefectLevel = -1
        defect_url = ""
        isArea = false

        if (!item) {
            return
        }

        id_ = item.Id || 0
        coilId = item.secondaryCoilId || 0
        surface = item.surface || "S"
        defectClass = item.defectClass || 0
        defectName = item.defectName || ""
        configDefectName = item.configDefectName || item.defectName || ""
        defectStatus = item.defectStatus || 0
        defectX = item.defectX || 0
        defectY = item.defectY || 0
        defectW = item.defectW || 0
        defectH = item.defectH || 0
        defectSource = item.defectSource || 0
        defectData = item.defectData
        apiDefectLevel = item.defectLevel !== undefined ? item.defectLevel : -1
        defect_url = api.get_defect_url(
            surface,
            coilId,
            defectName,
            defectX,
            defectY,
            defectW,
            defectH
        )
        isArea = item.is_area ?? false
    }
}
