import QtQuick
import QtQuick.Controls
import QtQuick.Layouts

ScrollView {
    id: root
    clip: true

    property bool loading: false
    property string statusText: ""

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

    function safeParse(data) {
        try {
            return JSON.parse(data)
        } catch (e) {
            return null
        }
    }

    function formatAge(value) {
        let age = Number(value)
        if (!isFinite(age)) {
            return "-"
        }
        return age.toFixed(1) + " s"
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
        if (loading) {
            return
        }
        loading = true
        statusText = qsTr("刷新中")
        app.api.getCameraAdjustments(function(data) {
            loading = false
            let payload = safeParse(data)
            if (payload && payload.cameras) {
                syncModel(payload.cameras)
                statusText = qsTr("已刷新")
            } else {
                statusText = qsTr("相机状态解析失败")
            }
        }, function(error) {
            loading = false
            statusText = qsTr("相机状态获取失败")
            console.log("getCameraAdjustments failed", error)
        })
    }

    function updateCamera(index, exposureTime, gain) {
        if (index < 0 || index >= cameraModel.count) {
            return
        }
        let item = cameraModel.get(index)
        cameraModel.setProperty(index, "busy", true)
        statusText = item.key + qsTr(" 保存中")
        app.api.setCameraAdjustment(item.key, exposureTime, gain, true, function(data) {
            cameraModel.setProperty(index, "busy", false)
            statusText = item.key + qsTr(" 已保存")
            root.refresh()
        }, function(error) {
            cameraModel.setProperty(index, "busy", false)
            statusText = item.key + qsTr(" 保存失败")
            console.log("setCameraAdjustment failed", error)
        })
    }

    function reconnectCamera(index) {
        if (index < 0 || index >= cameraModel.count) {
            return
        }
        let item = cameraModel.get(index)
        cameraModel.setProperty(index, "busy", true)
        statusText = item.key + qsTr(" 重连中")
        app.api.reconnectCameraAdjustment(item.key, function(data) {
            cameraModel.setProperty(index, "busy", false)
            statusText = item.key + qsTr(" 已发送重连")
            root.refresh()
        }, function(error) {
            cameraModel.setProperty(index, "busy", false)
            statusText = item.key + qsTr(" 重连失败")
            console.log("reconnectCameraAdjustment failed", error)
        })
    }

    function statusColor(connected, ok) {
        if (connected && ok) {
            return "#2EAD4B"
        }
        if (connected) {
            return "#D88912"
        }
        return "#B3261E"
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
                    color: coreStyle.labelColor
                    font.pixelSize: 13
                    Layout.fillWidth: true
                }

                Button {
                    text: root.loading ? qsTr("刷新中") : qsTr("刷新")
                    enabled: !root.loading
                    onClicked: root.refresh()
                }
            }

            Rectangle {
                Layout.fillWidth: true
                Layout.preferredHeight: 1
                color: coreStyle.headerBorderColor
            }

            Repeater {
                model: cameraModel

                delegate: Rectangle {
                    id: rowRoot
                    Layout.fillWidth: true
                    implicitHeight: rowLayout.implicitHeight + 18
                    color: "transparent"
                    border.color: coreStyle.headerBorderColor
                    border.width: 1
                    radius: coreStyle.controlRadius

                    RowLayout {
                        id: rowLayout
                        anchors.fill: parent
                        anchors.margins: 9
                        spacing: 12

                        Rectangle {
                            Layout.preferredWidth: 10
                            Layout.preferredHeight: 38
                            radius: 5
                            color: root.statusColor(model.connected, model.ok)
                        }

                        ColumnLayout {
                            Layout.fillWidth: true
                            Layout.minimumWidth: 220
                            spacing: 4

                            RowLayout {
                                spacing: 8
                                Layout.fillWidth: true

                                Label {
                                    text: model.key
                                    color: coreStyle.titleColor
                                    font.pixelSize: 15
                                    font.bold: true
                                }

                                Label {
                                    text: model.connected ? qsTr("在线") : qsTr("离线")
                                    color: root.statusColor(model.connected, model.ok)
                                    font.pixelSize: 13
                                }
                            }

                            Label {
                                text: (model.name || "-") + "  SN: " + (model.sn || "-")
                                color: coreStyle.labelColor
                                font.pixelSize: 12
                                elide: Text.ElideRight
                                Layout.fillWidth: true
                            }

                            Label {
                                text: qsTr("最近帧") + ": " + root.formatAge(model.lastFrameAge)
                                      + "    3D: " + root.formatAge(model.lastFrameAge3D)
                                      + "    " + qsTr("参数源") + ": " + (model.source || "-")
                                color: coreStyle.labelColor
                                opacity: 0.76
                                font.pixelSize: 12
                                elide: Text.ElideRight
                                Layout.fillWidth: true
                            }

                            Label {
                                text: model.message || model.lastError3D || model.serviceUrl || model.paramFile || model.yamlConfig
                                color: coreStyle.labelColor
                                opacity: 0.68
                                font.pixelSize: 11
                                elide: Text.ElideMiddle
                                Layout.fillWidth: true
                            }
                        }

                        ColumnLayout {
                            spacing: 6
                            Layout.preferredWidth: 150

                            Label {
                                text: qsTr("曝光时间")
                                color: coreStyle.labelColor
                                font.pixelSize: 12
                            }

                            SpinBox {
                                id: exposureBox
                                from: 1
                                to: 1000000
                                value: model.exposureTime
                                editable: true
                                enabled: model.writable && !model.busy
                                Layout.fillWidth: true
                            }
                        }

                        ColumnLayout {
                            spacing: 6
                            Layout.preferredWidth: 120

                            Label {
                                text: qsTr("增益")
                                color: coreStyle.labelColor
                                font.pixelSize: 12
                            }

                            SpinBox {
                                id: gainBox
                                from: 0
                                to: 1000
                                value: model.gain
                                editable: true
                                enabled: model.writable && !model.busy
                                Layout.fillWidth: true
                            }
                        }

                        ColumnLayout {
                            spacing: 6
                            Layout.preferredWidth: 88

                            Button {
                                text: model.busy ? qsTr("处理中") : qsTr("保存")
                                enabled: model.writable && !model.busy
                                Layout.fillWidth: true
                                onClicked: root.updateCamera(index, exposureBox.value, gainBox.value)
                            }

                            Button {
                                text: qsTr("重连")
                                enabled: !model.busy
                                Layout.fillWidth: true
                                onClicked: root.reconnectCamera(index)
                            }
                        }
                    }
                }
            }
        }

        Item {
            Layout.fillWidth: true
            Layout.fillHeight: true
        }
    }

    Component.onCompleted: refresh()

    component Section: Rectangle {
        id: section
        property string title: ""
        default property alias content: body.data

        Layout.fillWidth: true
        implicitHeight: sectionLayout.implicitHeight + 28
        color: coreStyle.panelElevatedColor
        border.color: coreStyle.headerBorderColor
        border.width: 1
        radius: coreStyle.controlRadius

        ColumnLayout {
            id: sectionLayout
            anchors.fill: parent
            anchors.margins: 14
            spacing: 12

            Label {
                text: section.title
                color: coreStyle.titleColor
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
