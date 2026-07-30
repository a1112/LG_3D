pragma ComponentBehavior: Bound
import QtQuick
import QtQuick.Controls
import QtQuick.Layouts

Item {
    id: root

    required property var watcher
    required property var style
    required property var apiClient
    required property var coreController
    property string globalKey: ""
    property int alarmLevel: 0
    property ListModel cameraModel: ListModel {}

    function syncStatus(payload) {
        if (!payload || typeof payload !== "object") {
            return
        }
        cameraModel.clear()
        for (let key in payload) {
            let item = payload[key] || {}
            cameraModel.append({
                "cameraKey": key,
                "level": Number(item.level || 0),
                "msg": item.msg || ""
            })
        }
    }

    Connections {
        target: root.watcher
        function onStatusPayloadChanged() {
            root.syncStatus(root.watcher.statusPayload)
        }
    }

    Component.onCompleted: root.syncStatus(root.watcher.statusPayload)

    ColumnLayout {
        anchors.fill: parent

        Label {
            text: qsTr("相机状态")
            font.pointSize: 18
            font.bold: true
            color: root.style.titleColor
            font.family: "Microsoft YaHei"
            Layout.alignment: Qt.AlignHCenter
        }

        GridView {
            id: cameraGrid
            Layout.fillWidth: true
            Layout.fillHeight: true
            model: root.cameraModel
            cellWidth: width / 3
            cellHeight: Math.max(36, height / 2)
            reuseItems: true

            delegate: AlarmItemCamerasItem {
                id: cameraDelegate
                style: root.style
                width: cameraGrid.cellWidth
                height: cameraGrid.cellHeight

                TapHandler {
                    acceptedButtons: Qt.RightButton
                    onTapped: {
                        root.globalKey = cameraDelegate.cameraKey
                        cameraIdMenu.popup()
                    }
                }
            }
        }
    }

    Menu {
        id: cameraIdMenu

        MenuItem {
            text: qsTr("打开当前卷相机数据")
            enabled: root.globalKey !== ""
            onTriggered: Qt.openUrlExternally(
                             root.apiClient.getCameraDataUrl(
                                 root.coreController.coilIndex,
                                 root.globalKey))
        }
    }
}
