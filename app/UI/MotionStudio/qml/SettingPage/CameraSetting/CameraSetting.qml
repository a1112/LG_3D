pragma ComponentBehavior: Bound

import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import "../../Core/JsonUtils.js" as JsonUtils

ScrollView {
    id: root
    required property var apiClient
    required property var style

    clip: true

    property bool loading: false
    property int actionCount: 0
    property int requestGeneration: 0
    property string statusText: ""
    readonly property bool busy: loading || actionCount > 0

    ListModel {
        id: cameraModel
        dynamicRoles: true
    }

    Timer {
        interval: 5000
        repeat: true
        running: root.visible
        onTriggered: root.refresh()
    }

    function paramValue(params, key) {
        if (params === undefined || params === null || params[key] === undefined || params[key] === null) {
            return 0
        }
        let value = Number(params[key])
        return isFinite(value) ? value : 0
    }

    function syncModel(cameras) {
        cameraModel.clear()
        for (let i = 0; i < cameras.length; i++) {
            let item = cameras[i]
            let status = item.status || {}
            let capture = status.capture || {}
            let params = status.params || {}
            cameraModel.append({
                                   key: item.key || "",
                                   name: item.name || "",
                                   sn: item.sn || "",
                                   yamlConfig: item.yamlConfig || status.yamlConfig || "",
                                   serviceUrl: item.serviceUrl || "",
                                   ok: status.ok === true,
                                   connected: status.connected === true,
                                   writable: status.writable === true,
                                   message: status.message || "",
                                   source: status.source || "",
                                   paramFile: status.paramFile || "",
                                   lastFrameAge: paramValue(status, "lastFrameAge"),
                                   lastFrameAge3D: paramValue(status, "lastFrameAge3D"),
                                   lastError3D: status.lastError3D || "",
                                   captureRunning: capture.captureRunning === true,
                                   serviceReady: capture.serviceReady !== false,
                                   exposureTime: paramValue(params, "exposureTime"),
                                   gain: paramValue(params, "gain"),
                                   busy: false
                               })
        }
    }

    function refresh() {
        if (root.busy) {
            return
        }
        let generation = ++root.requestGeneration
        root.loading = true
        root.statusText = qsTr("刷新中")
        root.apiClient.getCameraAdjustments(function(data) {
            if (generation !== root.requestGeneration)
                return
            root.loading = false
            let payload = JsonUtils.parse(data, null, "camera adjustments")
            if (payload && payload.cameras) {
                root.syncModel(payload.cameras)
                root.statusText = qsTr("已刷新")
            } else {
                root.statusText = qsTr("相机状态解析失败")
            }
        }, function(error) {
            if (generation !== root.requestGeneration)
                return
            root.loading = false
            root.statusText = qsTr("相机状态获取失败")
            console.log("getCameraAdjustments failed", error)
        })
    }

    function updateCamera(index, exposureTime, gain) {
        if (index < 0 || index >= cameraModel.count) {
            return
        }
        let item = cameraModel.get(index)
        cameraModel.setProperty(index, "busy", true)
        root.actionCount += 1
        root.statusText = item.key + qsTr(" 保存中")
        root.apiClient.setCameraAdjustment(
                    item.key, exposureTime, gain, true, function(data) {
            root.finishAction(index, item.key)
            root.statusText = item.key + qsTr(" 已保存")
            root.refresh()
        }, function(error) {
            root.finishAction(index, item.key)
            root.statusText = item.key + qsTr(" 保存失败")
            console.log("setCameraAdjustment failed", error)
        })
    }

    function reconnectCamera(index) {
        if (index < 0 || index >= cameraModel.count) {
            return
        }
        let item = cameraModel.get(index)
        cameraModel.setProperty(index, "busy", true)
        root.actionCount += 1
        root.statusText = item.key + qsTr(" 重连中")
        root.apiClient.reconnectCameraAdjustment(item.key, function(data) {
            root.finishAction(index, item.key)
            root.statusText = item.key + qsTr(" 已发送重连")
            root.refresh()
        }, function(error) {
            root.finishAction(index, item.key)
            root.statusText = item.key + qsTr(" 重连失败")
            console.log("reconnectCameraAdjustment failed", error)
        })
    }

    function finishAction(index, cameraKey) {
        root.actionCount = Math.max(0, root.actionCount - 1)
        if (index >= 0 && index < cameraModel.count
                && cameraModel.get(index).key === cameraKey) {
            cameraModel.setProperty(index, "busy", false)
        }
    }

    ColumnLayout {
        width: root.availableWidth
        spacing: 14
        anchors.margins: 20

        Item {
            Layout.fillWidth: true
            Layout.preferredHeight: 1
        }

        Section {
            title: qsTr("2D 相机调整")

            RowLayout {
                Layout.fillWidth: true
                spacing: 12

                Label {
                    text: qsTr("状态") + ": " + root.statusText
                    color: root.style.labelColor
                    font.pixelSize: 13
                    Layout.fillWidth: true
                }

                Button {
                    text: root.busy ? qsTr("处理中") : qsTr("刷新")
                    enabled: !root.busy
                    onClicked: root.refresh()
                }
            }

            Rectangle {
                Layout.fillWidth: true
                Layout.preferredHeight: 1
                color: root.style.headerBorderColor
            }

            Repeater {
                model: cameraModel

                delegate: CameraAdjustmentRow {
                    style: root.style
                    onSaveRequested:
                        (rowIndex, exposureTime, gain) =>
                            root.updateCamera(
                                rowIndex, exposureTime, gain)
                    onReconnectRequested:
                        rowIndex => root.reconnectCamera(rowIndex)
                }
            }
        }

        Item {
            Layout.fillWidth: true
            Layout.fillHeight: true
        }
    }

    Component.onCompleted: root.refresh()

    component Section: Rectangle {
        id: section
        property string title: ""
        default property alias content: body.data

        Layout.fillWidth: true
        implicitHeight: sectionLayout.implicitHeight + 28
        color: root.style.panelElevatedColor
        border.color: root.style.headerBorderColor
        border.width: 1
        radius: root.style.controlRadius

        ColumnLayout {
            id: sectionLayout
            anchors.fill: parent
            anchors.margins: 14
            spacing: 12

            Label {
                text: section.title
                color: root.style.titleColor
                font.pixelSize: 16
                font.bold: true
                Layout.fillWidth: true
            }

            ColumnLayout {
                id: body
                Layout.fillWidth: true
                spacing: 10
            }
        }
    }
}
