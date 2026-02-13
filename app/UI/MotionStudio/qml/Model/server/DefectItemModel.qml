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
    property bool isArea:false

    // 存储从 API 获取的 defectLevel（如果有的话）
    property int apiDefectLevel: -1

    // defectLevel 优先使用 API 返回的值，否则从配置中获取
    property int defectLevel: {
        if (apiDefectLevel >= 0) {
            return apiDefectLevel
        } else if (defectName) {
            return global.defectClassProperty.getDefectLevelByDefectName(defectName)
        } else {
            return 0
        }
    }

    property color defectColor: global.defectClassProperty.getColorByName(defectName)

    function init(item){
        // 重置所有属性
        id_ = 0
        coilId = 0
        surface = "S"
        defectClass = 0
        defectName = ""
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
        defectStatus = item.defectStatus || 0
        defectX = item.defectX || 0
        defectY = item.defectY || 0
        defectW = item.defectW || 0
        defectH = item.defectH || 0
        defectSource = item.defectSource || 0
        defectData = item.defectData
        // 如果 API 返回了 defectLevel，保存它
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
        isArea = item.is_area??false
    }

    property string defect_url:""
}
