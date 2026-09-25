pragma ComponentBehavior: Bound

import QtQuick
import QtQuick.Controls
import QtQuick.Controls.Material
import QtQuick.Layouts
import "../Base"
import "../../Core/JsonUtils.js" as JsonUtils
import "HardwareMonitorFormat.js" as Format

PopupBase {
    id: root

    required property var apiClient
    required property var adaptiveMetrics
    required property var style

    width: adaptiveMetrics.boundedWidth(1500, 1100, 1780)
    height: adaptiveMetrics.boundedHeight(880, 700, 1000)
    anchors.centerIn: parent
    modal: true
    focus: true
    closePolicy: Popup.CloseOnEscape

    property bool loading: false
    property bool autoRefresh: true
    property string statusText: "等待刷新"
    property double updatedAt: 0
    property int cameraOnline: 0
    property int cameraCount: 0
    property int camera2DOnline: 0
    property int camera2DCount: 0
    property int camera3DOnline: 0
    property int camera3DCount: 0
    property int networkOnline: 0
    property int networkCount: 0
    property int serviceOnline: 0
    property int serviceCount: 0
    property int temperatureSensorCount: 0
    property real maxTemperature: 0
    property bool maxTemperatureAvailable: false

    ListModel {
        id: cameraModel
        dynamicRoles: true
    }

    ListModel {
        id: networkModel
        dynamicRoles: true
    }

    ListModel {
        id: serviceModel
        dynamicRoles: true
    }

    Timer {
        id: autoRefreshTimer
        interval: 1000
        repeat: true
        running: root.opened && root.autoRefresh
        onTriggered: root.refresh()
    }

    Timer {
        id: refreshDelayTimer
        interval: 3000
        repeat: false
        onTriggered: root.refresh()
    }

    function numberValue(value) {
        let result = Number(value)
        return isFinite(result) ? result : 0
    }

    function optionalNumber(value) {
        if (value === undefined || value === null || value === "") {
            return null
        }
        let result = Number(value)
        return isFinite(result) ? result : null
    }

    function syncCameras(cameras) {
        cameraModel.clear()
        for (let i = 0; i < cameras.length; ++i) {
            let item = cameras[i] || {}
            let camera2D = item.camera2D || {}
            let camera3D = item.camera3D || {}
            let params = camera2D.params || {}
            let cap2D = item.cap2D === true
            let cap3D = item.cap3D === true
            let ok2D = cap2D && camera2D.ok === true
            let ok3D = cap3D && camera3D.ok === true
            let serviceReady = item.serviceReady === true
            let age2D = camera2D.lastFrameAge
            if (age2D === undefined || age2D === null) {
                age2D = item.lastFrameAge2D
            }
            let age3D = camera3D.lastFrameAge
            if (age3D === undefined || age3D === null) {
                age3D = item.lastFrameAge3D
            }
            cameraModel.append({
                cameraKey: item.key || "",
                cameraName: item.name || "",
                sn: item.sn || camera3D.sn || "",
                cap2D: cap2D,
                cap3D: cap3D,
                camera2DOk: ok2D,
                camera3DOk: ok3D,
                camera2DConnected: camera2D.connected === true,
                camera3DConnected: camera3D.connected === true,
                camera3DAcquiring: camera3D.acquiring === true,
                captureRunning: item.captureRunning === true,
                serviceReady: serviceReady,
                healthy: serviceReady
                         && (!cap2D || ok2D)
                         && (!cap3D || ok3D)
                         && !item.lastError2D && !item.lastError3D,
                lastFrameAge2D: numberValue(age2D),
                hasFrame2D: age2D !== undefined && age2D !== null,
                lastFrameAge3D: numberValue(age3D),
                hasFrame3D: age3D !== undefined && age3D !== null,
                error2D: item.lastError2D || camera2D.lastError
                         || camera2D.message || "",
                error3D: item.lastError3D || camera3D.lastError || "",
                startFailures: numberValue(camera3D.consecutiveStartFailures),
                last3DAction: camera3D.lastAction || "",
                state2D: camera2D.state || "",
                frameId2D: numberValue(camera2D.frameId),
                emptyFrames2D: numberValue(camera2D.emptyFrameCount),
                frameErrors2D: numberValue(camera2D.frameErrorCount),
                droppedFrames2D: numberValue(camera2D.droppedFrames),
                connectAttempts2D: numberValue(camera2D.connectAttempts),
                width2D: numberValue(camera2D.width),
                height2D: numberValue(camera2D.height),
                queueSize2D: numberValue(camera2D.queueSize),
                exposureTime2D: optionalNumber(params.exposureTime),
                gain2D: optionalNumber(params.gain),
                temperature2D: optionalNumber(camera2D.temperatureCelsius),
                temperature2DAvailable:
                    camera2D.temperatureAvailable === true,
                temperature2DStale: camera2D.temperatureStale === true,
                temperature2DSource: camera2D.temperatureSource || "",
                temperature2DError: camera2D.temperatureError || "",
                temperature3D: optionalNumber(camera3D.temperatureCelsius),
                temperature3DAvailable:
                    camera3D.temperatureAvailable === true,
                temperature3DStale: camera3D.temperatureStale === true,
                temperature3DSource: camera3D.temperatureSource || "",
                temperature3DError: camera3D.temperatureError || "",
                busy: false
            })
        }
    }

    function syncNetworks(adapters) {
        networkModel.clear()
        for (let i = 0; i < adapters.length; ++i) {
            let item = adapters[i] || {}
            networkModel.append({
                adapterName: item.name || "",
                isUp: item.isUp === true,
                speedMbps: numberValue(item.speedMbps),
                mtu: numberValue(item.mtu),
                duplex: item.duplex || "",
                mac: item.mac || "",
                ipv4: (item.ipv4 || []).join(", "),
                ipv6: (item.ipv6 || []).join(", "),
                rxBytesPerSecond: numberValue(item.rxBytesPerSecond),
                txBytesPerSecond: numberValue(item.txBytesPerSecond),
                bytesReceived: numberValue(item.bytesReceived),
                bytesSent: numberValue(item.bytesSent),
                packetsReceived: numberValue(item.packetsReceived),
                packetsSent: numberValue(item.packetsSent),
                errors: numberValue(item.errorsIn) + numberValue(item.errorsOut),
                drops: numberValue(item.dropsIn) + numberValue(item.dropsOut),
                canControl: item.canControl === true,
                controlReason: item.controlReason || "",
                busy: false
            })
        }
    }

    function syncServices(services) {
        serviceModel.clear()
        for (let i = 0; i < services.length; ++i) {
            let item = services[i] || {}
            serviceModel.append({
                serviceKey: item.key || "",
                serviceName: item.name || "",
                category: item.category || "",
                canRestart: item.canRestart === true,
                online: item.online === true,
                state: item.state || "",
                stateText: item.stateText || "",
                host: item.host || "",
                port: numberValue(item.port),
                hasPort: item.port !== undefined && item.port !== null,
                pid: numberValue(item.pid),
                hasPid: item.pid !== undefined && item.pid !== null,
                processName: item.processName || "",
                commandLine: item.commandLine || "",
                uptimeSeconds: numberValue(item.uptimeSeconds),
                hasUptime: item.uptimeSeconds !== undefined
                           && item.uptimeSeconds !== null,
                memoryBytes: numberValue(item.memoryBytes),
                processCount: numberValue(item.processCount),
                message: item.message || "",
                busy: false
            })
        }
    }

    function refresh() {
        if (root.loading) {
            return
        }
        root.loading = true
        root.statusText = "刷新中"
        root.apiClient.getHardwareMonitor(function(data) {
            root.loading = false
            let payload = JsonUtils.parse(data, null, "hardware monitor")
            if (!payload) {
                root.statusText = "状态解析失败"
                return
            }
            let summary = payload.summary || {}
            root.syncCameras(payload.cameras || [])
            root.syncNetworks(payload.networkAdapters || [])
            root.syncServices(payload.services || [])
            root.cameraOnline = numberValue(summary.cameraOnline)
            root.cameraCount = numberValue(summary.cameraCount)
            root.camera2DOnline = numberValue(summary.camera2DOnline)
            root.camera2DCount = numberValue(summary.camera2DCount)
            root.camera3DOnline = numberValue(summary.camera3DOnline)
            root.camera3DCount = numberValue(summary.camera3DCount)
            root.networkOnline = numberValue(summary.networkAdapterOnline)
            root.networkCount = numberValue(summary.networkAdapterCount)
            root.serviceOnline = numberValue(summary.serviceOnline)
            root.serviceCount = numberValue(summary.serviceCount)
            root.temperatureSensorCount =
                    numberValue(summary.temperatureSensorCount)
            root.maxTemperatureAvailable =
                    summary.maxTemperatureCelsius !== undefined
                    && summary.maxTemperatureCelsius !== null
            root.maxTemperature =
                    numberValue(summary.maxTemperatureCelsius)
            root.updatedAt = numberValue(payload.time)
            root.statusText = payload.networkError
                              ? "网卡状态异常: " + payload.networkError
                              : payload.serviceError
                                ? "服务状态异常: " + payload.serviceError
                                : "实时状态"
        }, function(error) {
            root.loading = false
            root.statusText = "监控服务连接失败"
            console.log("getHardwareMonitor failed", error)
        })
    }

    function runCameraAction(index, action) {
        if (index < 0 || index >= cameraModel.count) {
            return
        }
        let item = cameraModel.get(index)
        cameraModel.setProperty(index, "busy", true)
        root.statusText = item.cameraKey + " 控制中"
        let success = function(data) {
            cameraModel.setProperty(index, "busy", false)
            root.statusText = item.cameraKey + " 控制命令已完成"
            root.refresh()
        }
        let failure = function(error) {
            cameraModel.setProperty(index, "busy", false)
            root.statusText = item.cameraKey + " 控制失败"
            console.log("camera control failed", error)
        }
        if (action === "reconnect2d") {
            root.apiClient.reconnectCamera2D(item.cameraKey, success, failure)
        } else if (action === "reconnect3d") {
            root.apiClient.reconnectCamera3D(item.cameraKey, success, failure)
        } else if (action === "reset3d") {
            root.apiClient.resetCamera3D(item.cameraKey, success, failure)
        }
    }

    function runNetworkAction(index, action) {
        if (index < 0 || index >= networkModel.count) {
            return
        }
        let item = networkModel.get(index)
        networkModel.setProperty(index, "busy", true)
        root.statusText = item.adapterName + " 控制中"
        root.apiClient.controlNetworkAdapter(
                    item.adapterName, action, function(data) {
            networkModel.setProperty(index, "busy", false)
            root.statusText = item.adapterName + " 控制命令已完成"
            root.refresh()
        }, function(error) {
            networkModel.setProperty(index, "busy", false)
            root.statusText = item.adapterName + " 控制失败"
            console.log("network adapter control failed", error)
        })
    }

    function runServiceRestart(index) {
        if (index < 0 || index >= serviceModel.count) {
            return
        }
        let item = serviceModel.get(index)
        serviceModel.setProperty(index, "busy", true)
        root.statusText = item.serviceName + " 重启中"
        root.apiClient.restartService(item.serviceKey, function(data) {
            serviceModel.setProperty(index, "busy", false)
            root.statusText = item.serviceName + " 已提交重启"
            refreshDelayTimer.restart()
        }, function(error) {
            serviceModel.setProperty(index, "busy", false)
            root.statusText = item.serviceName + " 重启失败"
            console.log("service restart failed", error)
        })
    }

    function confirmServiceRestart(index) {
        let item = serviceModel.get(index)
        confirmDialog.targetKind = "service"
        confirmDialog.targetIndex = index
        confirmDialog.targetAction = "restart"
        confirmDialog.targetName = item.serviceName
        confirmDialog.message = "重启会短暂中断该服务，确认继续重启 "
                                + item.serviceName + "？"
        confirmDialog.open()
    }

    function confirmCameraReset(index) {
        let item = cameraModel.get(index)
        confirmDialog.targetKind = "camera"
        confirmDialog.targetIndex = index
        confirmDialog.targetAction = "reset3d"
        confirmDialog.targetName = item.cameraKey
        confirmDialog.message = "设备复位会中断该路 3D 采集并重新连接，确认继续？"
        confirmDialog.open()
    }

    function confirmNetworkAction(index, action) {
        let item = networkModel.get(index)
        confirmDialog.targetKind = "network"
        confirmDialog.targetIndex = index
        confirmDialog.targetAction = action
        confirmDialog.targetName = item.adapterName
        confirmDialog.message = (action === "disable"
                                 ? "禁用网卡会立即中断该网卡上的相机或服务连接。"
                                 : action === "restart"
                                   ? "重启网卡会短暂中断该网卡上的全部连接。"
                                   : "确认启用该网卡？")
                                + "\n确认继续操作 " + item.adapterName + "？"
        confirmDialog.open()
    }

    onOpened: refresh()

    ColumnLayout {
        anchors.fill: parent
        anchors.margins: root.adaptiveMetrics.mainSpacing
        spacing: 8

        RowLayout {
            Layout.fillWidth: true
            spacing: root.adaptiveMetrics.mainSpacing

            Label {
                text: "设备与服务实时监控"
                color: root.style.titleColor
                font.pixelSize: root.adaptiveMetrics.fontMetric(21, 18, 26)
                font.bold: true
                Layout.fillWidth: true
            }

            CheckBox {
                text: "自动刷新"
                checked: root.autoRefresh
                onToggled: root.autoRefresh = checked
            }

            Button {
                text: root.loading ? "刷新中" : "立即刷新"
                enabled: !root.loading
                onClicked: root.refresh()
            }

            Button {
                text: "关闭"
                onClicked: root.close()
            }
        }

        Rectangle {
            Layout.fillWidth: true
            Layout.preferredHeight: 46
            color: root.style.panelAlternateColor
            border.color: root.style.headerBorderColor
            radius: root.style.controlRadius

            RowLayout {
                anchors.fill: parent
                anchors.margins: 9
                spacing: 22

                MonitorCompactSummary {
                    style: root.style
                    label: "3D"
                    value: root.camera3DOnline + "/" + root.camera3DCount
                    healthy: root.camera3DOnline === root.camera3DCount
                }

                MonitorCompactSummary {
                    style: root.style
                    label: "2D"
                    value: root.camera2DOnline + "/" + root.camera2DCount
                    healthy: root.camera2DOnline === root.camera2DCount
                }

                MonitorCompactSummary {
                    style: root.style
                    label: "网卡"
                    value: root.networkOnline + "/" + root.networkCount
                    healthy: root.networkOnline === root.networkCount
                }

                MonitorCompactSummary {
                    style: root.style
                    label: "服务"
                    value: root.serviceOnline + "/" + root.serviceCount
                    healthy: root.serviceOnline === root.serviceCount
                }

                Label {
                    text: "最高温 "
                          + (root.maxTemperatureAvailable
                             ? root.maxTemperature.toFixed(1) + " °C"
                             : "-- °C")
                    color: Format.temperatureColor(
                               root.style,
                               root.maxTemperatureAvailable,
                               root.maxTemperature,
                               false)
                    font.bold: true
                }

                Label {
                    text: root.statusText
                    color: root.style.labelColor
                    Layout.fillWidth: true
                    elide: Text.ElideRight
                }

                Label {
                    text: root.updatedAt > 0
                          ? Qt.formatDateTime(
                                new Date(root.updatedAt * 1000),
                                "yyyy-MM-dd hh:mm:ss")
                          : "-"
                    color: root.style.secondaryTextColor
                    opacity: 0.72
                }
            }
        }

        TabBar {
            id: tabBar
            Layout.fillWidth: true

            TabButton { text: "总览" }
            TabButton {
                text: "3D 相机  " + root.camera3DOnline
                      + "/" + root.camera3DCount
            }
            TabButton {
                text: "2D 相机  " + root.camera2DOnline
                      + "/" + root.camera2DCount
            }
            TabButton {
                text: "网卡  " + root.networkOnline
                      + "/" + root.networkCount
            }
            TabButton {
                text: "服务  " + root.serviceOnline
                      + "/" + root.serviceCount
            }
        }

        StackLayout {
            Layout.fillWidth: true
            Layout.fillHeight: true
            currentIndex: tabBar.currentIndex

            Item {
                ColumnLayout {
                    anchors.fill: parent
                    spacing: 8

                    RowLayout {
                        Layout.fillWidth: true
                        spacing: 8

                        MonitorKpiCard {
                            style: root.style
                            title: "3D 相机"
                            value: root.camera3DOnline + " / "
                                   + root.camera3DCount
                            detail: "连接并采集中"
                            accent: root.camera3DOnline === root.camera3DCount
                                    ? root.style.statusSuccessColor
                                    : root.style.statusWarningColor
                        }

                        MonitorKpiCard {
                            style: root.style
                            title: "2D 相机"
                            value: root.camera2DOnline + " / "
                                   + root.camera2DCount
                            detail: "连接 / 等待触发"
                            accent: root.camera2DOnline === root.camera2DCount
                                    ? root.style.statusSuccessColor
                                    : root.style.statusWarningColor
                        }

                        MonitorKpiCard {
                            style: root.style
                            title: "设备温度"
                            value: root.maxTemperatureAvailable
                                   ? root.maxTemperature.toFixed(1) + " °C"
                                   : "-- °C"
                            detail: root.temperatureSensorCount
                                    + " 个温度传感器"
                            accent: Format.temperatureColor(
                                        root.style,
                                        root.maxTemperatureAvailable,
                                        root.maxTemperature,
                                        false)
                        }

                        MonitorKpiCard {
                            style: root.style
                            title: "网卡"
                            value: root.networkOnline + " / "
                                   + root.networkCount
                            detail: "在线适配器"
                            accent: root.networkOnline === root.networkCount
                                    ? root.style.statusSuccessColor
                                    : root.style.statusWarningColor
                        }

                        MonitorKpiCard {
                            style: root.style
                            title: "服务"
                            value: root.serviceOnline + " / "
                                   + root.serviceCount
                            detail: "核心进程 / 端口"
                            accent: root.serviceOnline === root.serviceCount
                                    ? root.style.statusSuccessColor
                                    : root.style.statusErrorColor
                        }
                    }

                    GridLayout {
                        Layout.fillWidth: true
                        Layout.fillHeight: true
                        columns: 2
                        columnSpacing: 8
                        rowSpacing: 8

                        MonitorPanel {
                            style: root.style
                            Layout.fillWidth: true
                            Layout.fillHeight: true
                            Layout.rowSpan: 2
                            Layout.preferredWidth: 850
                            panelTitle: "相机状态矩阵"
                            panelCaption: "一屏查看 3D / 2D、温度与故障"

                            GridView {
                                anchors.fill: parent
                                clip: true
                                cellWidth: width / (width >= 720 ? 2 : 1)
                                cellHeight: 102
                                model: cameraModel
                                ScrollBar.vertical: ScrollBar {}

                                delegate: MonitorOverviewCameraCard {
                                    width: GridView.view.cellWidth - 8
                                    height: GridView.view.cellHeight - 8
                                    style: root.style
                                }
                            }
                        }

                        MonitorPanel {
                            style: root.style
                            Layout.fillWidth: true
                            Layout.fillHeight: true
                            Layout.preferredWidth: 520
                            panelTitle: "服务运行"
                            panelCaption: root.serviceOnline + " / "
                                          + root.serviceCount + " 在线"

                            ListView {
                                anchors.fill: parent
                                clip: true
                                spacing: 4
                                model: serviceModel
                                ScrollBar.vertical: ScrollBar {}

                                delegate: MonitorOverviewServiceRow {
                                    width: ListView.view.width
                                    height: 34
                                    style: root.style
                                }
                            }
                        }

                        MonitorPanel {
                            style: root.style
                            Layout.fillWidth: true
                            Layout.fillHeight: true
                            panelTitle: "网卡运行"
                            panelCaption: root.networkOnline + " / "
                                          + root.networkCount + " 在线"

                            ListView {
                                anchors.fill: parent
                                clip: true
                                spacing: 4
                                model: networkModel
                                ScrollBar.vertical: ScrollBar {}

                                delegate: MonitorOverviewNetworkRow {
                                    width: ListView.view.width
                                    height: 42
                                    style: root.style
                                }
                            }
                        }
                    }
                }
            }

            Item {
                MonitorPanel {
                    style: root.style
                    anchors.fill: parent
                    panelTitle: "3D 相机"
                    panelCaption: "连接、采集、温度、帧状态及独立控制"

                    GridView {
                        anchors.fill: parent
                        clip: true
                        cellWidth: width / (width >= 1220 ? 3 : 2)
                        cellHeight: 224
                        model: cameraModel
                        ScrollBar.vertical: ScrollBar {}

                        delegate: MonitorCamera3DCard {
                            width: GridView.view.cellWidth - 10
                            height: GridView.view.cellHeight - 10
                            style: root.style
                            onReconnectRequested:
                                rowIndex => root.runCameraAction(
                                    rowIndex, "reconnect3d")
                            onResetRequested:
                                rowIndex => root.confirmCameraReset(rowIndex)
                        }
                    }
                }
            }

            Item {
                MonitorPanel {
                    style: root.style
                    anchors.fill: parent
                    panelTitle: "2D 相机"
                    panelCaption: "连接、触发等待、温度、帧计数与采集参数"

                    GridView {
                        anchors.fill: parent
                        clip: true
                        cellWidth: width / (width >= 1220 ? 3 : 2)
                        cellHeight: 250
                        model: cameraModel
                        ScrollBar.vertical: ScrollBar {}

                        delegate: MonitorCamera2DCard {
                            width: GridView.view.cellWidth - 10
                            height: GridView.view.cellHeight - 10
                            style: root.style
                            onReconnectRequested:
                                rowIndex => root.runCameraAction(
                                    rowIndex, "reconnect2d")
                        }
                    }
                }
            }

            Item {
                MonitorPanel {
                    style: root.style
                    anchors.fill: parent
                    panelTitle: "网卡"
                    panelCaption: "链路、地址、实时吞吐、错误 / 丢包与控制"

                    GridView {
                        anchors.fill: parent
                        clip: true
                        cellWidth: width / (width >= 1100 ? 2 : 1)
                        cellHeight: 190
                        model: networkModel
                        ScrollBar.vertical: ScrollBar {}

                        delegate: MonitorNetworkCard {
                            width: GridView.view.cellWidth - 10
                            height: GridView.view.cellHeight - 10
                            style: root.style
                            onActionRequested:
                                (rowIndex, action) =>
                                    root.confirmNetworkAction(rowIndex, action)
                        }
                    }
                }
            }

            Item {
                MonitorPanel {
                    style: root.style
                    anchors.fill: parent
                    panelTitle: "服务"
                    panelCaption: "现场核心、算法、通信、加速、基础与守护服务"

                    GridView {
                        anchors.fill: parent
                        clip: true
                        cellWidth: width / (width >= 1220 ? 3 : 2)
                        cellHeight: 178
                        model: serviceModel
                        ScrollBar.vertical: ScrollBar {}

                        delegate: MonitorServiceCard {
                            width: GridView.view.cellWidth - 10
                            height: GridView.view.cellHeight - 10
                            style: root.style
                            onRestartRequested:
                                rowIndex => root.confirmServiceRestart(rowIndex)
                        }
                    }
                }
            }
        }
    }

    Dialog {
        id: confirmDialog
        title: "确认设备控制"
        modal: true
        anchors.centerIn: parent
        width: 460

        property string targetKind: ""
        property int targetIndex: -1
        property string targetAction: ""
        property string targetName: ""
        property string message: ""

        contentItem: Label {
            text: confirmDialog.message
            color: root.style.labelColor
            wrapMode: Text.WordWrap
            padding: 18
        }

        standardButtons: Dialog.Ok | Dialog.Cancel
        onAccepted: {
            if (confirmDialog.targetKind === "camera") {
                root.runCameraAction(confirmDialog.targetIndex,
                                     confirmDialog.targetAction)
            } else if (confirmDialog.targetKind === "network") {
                root.runNetworkAction(confirmDialog.targetIndex,
                                      confirmDialog.targetAction)
            } else if (confirmDialog.targetKind === "service") {
                root.runServiceRestart(confirmDialog.targetIndex)
            }
        }
    }
}
