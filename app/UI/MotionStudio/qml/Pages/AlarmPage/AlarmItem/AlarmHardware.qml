pragma ComponentBehavior: Bound
import QtQuick 2.15
import QtQuick.Controls
import QtQuick.Controls.Material
import QtQuick.Layouts
import "../../../Core/JsonUtils.js" as JsonUtils
Item {
    id: root

    required property var apiClient
    required property var style

    property int alarmLevel: 0
    property bool requestRunning: false
    property var hardwareData: ({})
    property alias hardwareModel: hardwareListModel

    ListModel{
        id: hardwareListModel

    }
    Timer{
        id:getHardwareTimer
        running:root.visible
        repeat:true
        triggeredOnStart: true
        interval: 5000
        onTriggered:{
            if (root.requestRunning) {
                return
            }
            root.requestRunning = true
            root.apiClient.getHardware(
                        (res)=>{
                            root.requestRunning = false
                            let payload = JsonUtils.parse(res, null, "hardware alarm")
                            if (!payload || typeof payload !== "object") {
                                return
                            }
                            root.hardwareData = payload
                            // 清空并重新填充模型
                            root.hardwareModel.clear()
                            for (let key in root.hardwareData) {
                                let item = root.hardwareData[key]
                                // 确保 value 字段是字符串类型（与默认类型一致）
                                root.hardwareModel.append({
                                    "key": item.key || "",
                                    "value": String(item.value || ""),
                                    "msg": item.msg || "",
                                    "level": Number(item.level || 0)
                                })
                            }
                        },
                        (errorString)=>{
                            root.requestRunning = false
                            if (root.hardwareModel.count === 0) {
                                root.hardwareModel.append({
                                    "key": qsTr("服务器"),
                                    "value": qsTr("不可用"),
                                    "msg": String(errorString || qsTr("硬件状态请求失败")),
                                    "level": 3
                                })
                            }
                        }
                        )
        }
    }

    ColumnLayout{
    anchors.fill: parent
    Label{
        text:"服务器状态"
        font.pointSize: 15
        font.bold: true
        color: root.style.titleColor
        font.family: "Microsoft YaHei"
        Layout.alignment: Qt.AlignHCenter

    }
    Item{
        id:body
        Layout.fillWidth: true
        Layout.fillHeight: true
    GridView{
        id: hardwareGrid
        anchors.fill: parent
        model: root.hardwareModel
        cellWidth: parent.width / 2-1
        cellHeight: parent.height/2
        reuseItems: true
        delegate: AlarmItemHardwareItem {
            style: root.style
            width: hardwareGrid.cellWidth
            height: hardwareGrid.cellHeight
        }
    }
    }
}

}
