import QtQuick

Item {
    id: root

    property var pointDatas: []
    property ListModel pointDbData: ListModel {
        dynamicRoles: true
    }
    property ListModel pointUserData: ListModel {
        dynamicRoles: true
    }

    function clear() {
        root.pointUserData.clear()
        root.pointDbData.clear()
    }

    function addUserPoint(px, py) {
        root.pointUserData.append({
            "p_x": px,
            "p_y": py,
            "p_z": 0,
            "type": "user"
        })
    }

    function addDbPoint(dataItem) {
        if (!dataItem
                || dataItem.x === null || dataItem.x === undefined
                || dataItem.y === null || dataItem.y === undefined) {
            return
        }

        let zMm = Number(dataItem.z_mm)
        if (!isFinite(zMm) || zMm < 15) {
            return
        }

        let cleanItem = {}
        for (let key in dataItem) {
            if (dataItem[key] !== null && dataItem[key] !== undefined) {
                cleanItem[key] = dataItem[key]
            }
        }
        cleanItem.p_x = dataItem.x
        cleanItem.p_y = dataItem.y
        cleanItem.p_z = dataItem.z
        root.pointDbData.append(cleanItem)
    }

    function setDatas(data) {
        root.pointDatas = Array.isArray(data) ? data : []
        root.pointDatas.forEach(function(value) {
            root.addDbPoint(value)
        })
    }
}
