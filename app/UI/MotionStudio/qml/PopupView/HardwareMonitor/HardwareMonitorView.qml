import QtQuick
import QtQuick.Controls
import QtQuick.Controls.Material
import QtQuick.Layouts
import "../Base"

PopupBase {
    id: root

    width: adaptive.boundedWidth(1500, 1100, 1780)
    height: adaptive.boundedHeight(880, 700, 1000)
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

    function safeParse(data) {
        try {
            return JSON.parse(data)
        } catch (e) {
            return null
        }
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

    function formatAge(value) {
        if (value === undefined || value === null) {
            return "-"
        }
        let age = Number(value)
        return isFinite(age) ? age.toFixed(1) + " s" : "-"
    }

    function formatRate(value) {
        let bytes = numberValue(value)
        if (bytes >= 1073741824) {
            return (bytes / 1073741824).toFixed(1) + " GB/s"
        }
        if (bytes >= 1048576) {
            return (bytes / 1048576).toFixed(1) + " MB/s"
        }
        if (bytes >= 1024) {
            return (bytes / 1024).toFixed(1) + " KB/s"
        }
        return bytes.toFixed(0) + " B/s"
    }

    function formatBytes(value) {
        let bytes = numberValue(value)
        if (bytes >= 1073741824) {
            return (bytes / 1073741824).toFixed(1) + " GB"
        }
        if (bytes >= 1048576) {
            return (bytes / 1048576).toFixed(0) + " MB"
        }
        if (bytes >= 1024) {
            return (bytes / 1024).toFixed(0) + " KB"
        }
        return bytes.toFixed(0) + " B"
    }

    function formatDuration(value) {
        let seconds = Math.max(numberValue(value), 0)
        let days = Math.floor(seconds / 86400)
        let hours = Math.floor((seconds % 86400) / 3600)
        let minutes = Math.floor((seconds % 3600) / 60)
        if (days > 0) {
            return days + "天 " + hours + "小时"
        }
        if (hours > 0) {
            return hours + "小时 " + minutes + "分"
        }
        return minutes + "分"
    }

    function formatTemperature(available, value, stale) {
        if (!available || value === null || value === undefined) {
            return "-- °C"
        }
        return Number(value).toFixed(1) + " °C" + (stale ? " 旧" : "")
    }

    function temperatureAvailabilityText(error) {
        if (!error) {
            return ""
        }
        if (error.indexOf("0x80000106") >= 0
                || error.indexOf("0x80000100") >= 0) {
            return "设备未提供可读温度节点"
        }
        return error
    }

    function networkControlReason(reason) {
        if (reason === "loopback adapter cannot be controlled") {
            return "回环网卡不可控制"
        }
        if (reason === "network adapter control is only supported on Windows") {
            return "仅 Windows 支持网卡控制"
        }
        return reason
    }

    function temperatureColor(available, value, stale) {
        if (!available || stale) {
            return "#90A4AE"
        }
        let temperature = numberValue(value)
        if (temperature >= 70) {
            return "#EF5350"
        }
        if (temperature >= 55) {
            return "#FFB74D"
        }
        return "#4CAF69"
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
        app.api.getHardwareMonitor(function(data) {
            root.loading = false
            let payload = root.safeParse(data)
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
            app.api.reconnectCamera2D(item.cameraKey, success, failure)
        } else if (action === "reconnect3d") {
            app.api.reconnectCamera3D(item.cameraKey, success, failure)
        } else if (action === "reset3d") {
            app.api.resetCamera3D(item.cameraKey, success, failure)
        }
    }

    function runNetworkAction(index, action) {
        if (index < 0 || index >= networkModel.count) {
            return
        }
        let item = networkModel.get(index)
        networkModel.setProperty(index, "busy", true)
        root.statusText = item.adapterName + " 控制中"
        app.api.controlNetworkAdapter(item.adapterName, action, function(data) {
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
        app.api.restartService(item.serviceKey, function(data) {
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
        anchors.margins: adaptive.mainSpacing
        spacing: 8

        RowLayout {
            Layout.fillWidth: true
            spacing: adaptive.mainSpacing

            Label {
                text: "设备与服务实时监控"
                color: coreStyle.titleColor
                font.pixelSize: adaptive.fontMetric(21, 18, 26)
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
            color: coreStyle.panelAlternateColor
            border.color: coreStyle.headerBorderColor
            radius: coreStyle.controlRadius

            RowLayout {
                anchors.fill: parent
                anchors.margins: 9
                spacing: 22

                CompactSummary {
                    label: "3D"
                    value: root.camera3DOnline + "/" + root.camera3DCount
                    healthy: root.camera3DOnline === root.camera3DCount
                }

                CompactSummary {
                    label: "2D"
                    value: root.camera2DOnline + "/" + root.camera2DCount
                    healthy: root.camera2DOnline === root.camera2DCount
                }

                CompactSummary {
                    label: "网卡"
                    value: root.networkOnline + "/" + root.networkCount
                    healthy: root.networkOnline === root.networkCount
                }

                CompactSummary {
                    label: "服务"
                    value: root.serviceOnline + "/" + root.serviceCount
                    healthy: root.serviceOnline === root.serviceCount
                }

                Label {
                    text: "最高温 "
                          + (root.maxTemperatureAvailable
                             ? root.maxTemperature.toFixed(1) + " °C"
                             : "-- °C")
                    color: root.temperatureColor(
                               root.maxTemperatureAvailable,
                               root.maxTemperature,
                               false)
                    font.bold: true
                }

                Label {
                    text: root.statusText
                    color: coreStyle.labelColor
                    Layout.fillWidth: true
                    elide: Text.ElideRight
                }

                Label {
                    text: root.updatedAt > 0
                          ? Qt.formatDateTime(
                                new Date(root.updatedAt * 1000),
                                "yyyy-MM-dd hh:mm:ss")
                          : "-"
                    color: coreStyle.labelColor
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

                        KpiCard {
                            title: "3D 相机"
                            value: root.camera3DOnline + " / "
                                   + root.camera3DCount
                            detail: "连接并采集中"
                            accent: root.camera3DOnline
                                    === root.camera3DCount
                                    ? "#4CAF69" : "#FFB74D"
                        }

                        KpiCard {
                            title: "2D 相机"
                            value: root.camera2DOnline + " / "
                                   + root.camera2DCount
                            detail: "连接 / 等待触发"
                            accent: root.camera2DOnline
                                    === root.camera2DCount
                                    ? "#4CAF69" : "#FFB74D"
                        }

                        KpiCard {
                            title: "设备温度"
                            value: root.maxTemperatureAvailable
                                   ? root.maxTemperature.toFixed(1) + " °C"
                                   : "-- °C"
                            detail: root.temperatureSensorCount
                                    + " 个温度传感器"
                            accent: root.temperatureColor(
                                        root.maxTemperatureAvailable,
                                        root.maxTemperature,
                                        false)
                        }

                        KpiCard {
                            title: "网卡"
                            value: root.networkOnline + " / "
                                   + root.networkCount
                            detail: "在线适配器"
                            accent: root.networkOnline
                                    === root.networkCount
                                    ? "#4CAF69" : "#FFB74D"
                        }

                        KpiCard {
                            title: "服务"
                            value: root.serviceOnline + " / "
                                   + root.serviceCount
                            detail: "核心进程 / 端口"
                            accent: root.serviceOnline
                                    === root.serviceCount
                                    ? "#4CAF69" : "#EF5350"
                        }
                    }

                    GridLayout {
                        Layout.fillWidth: true
                        Layout.fillHeight: true
                        columns: 2
                        columnSpacing: 8
                        rowSpacing: 8

                        MonitorPanel {
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

                                delegate: Rectangle {
                                    width: GridView.view.cellWidth - 8
                                    height: GridView.view.cellHeight - 8
                                    color: coreStyle.panelAlternateColor
                                    border.color: model.healthy
                                                  ? "#3F8F63" : "#A85A50"
                                    radius: coreStyle.controlRadius

                                    ColumnLayout {
                                        anchors.fill: parent
                                        anchors.margins: 8
                                        spacing: 3

                                        RowLayout {
                                            Layout.fillWidth: true

                                            StatusDot {
                                                active: model.healthy
                                            }
                                            Label {
                                                text: model.cameraKey
                                                      + "  "
                                                      + model.cameraName
                                                color: coreStyle.titleColor
                                                font.bold: true
                                                Layout.fillWidth: true
                                                elide: Text.ElideRight
                                            }
                                            Label {
                                                text: model.captureRunning
                                                      ? "采集中" : "待采集"
                                                color: model.captureRunning
                                                       ? "#4CAF69"
                                                       : "#90A4AE"
                                            }
                                        }

                                        RowLayout {
                                            Layout.fillWidth: true
                                            Label {
                                                text: "3D "
                                                      + (model.camera3DOk
                                                         ? "正常" : "异常")
                                                      + "  "
                                                      + root.formatTemperature(
                                                          model.temperature3DAvailable,
                                                          model.temperature3D,
                                                          model.temperature3DStale)
                                                color: model.camera3DOk
                                                       ? "#4CAF69"
                                                       : "#FFB74D"
                                                Layout.fillWidth: true
                                            }
                                            Label {
                                                text: "2D "
                                                      + (model.camera2DOk
                                                         ? "正常" : "异常")
                                                      + "  "
                                                      + root.formatTemperature(
                                                          model.temperature2DAvailable,
                                                          model.temperature2D,
                                                          model.temperature2DStale)
                                                color: model.camera2DOk
                                                       ? "#4CAF69"
                                                       : "#FFB74D"
                                                Layout.fillWidth: true
                                            }
                                        }

                                        Label {
                                            text: model.error3D
                                                  || model.error2D
                                                  || "运行正常"
                                            color: model.error3D
                                                   || model.error2D
                                                   ? "#EF5350"
                                                   : coreStyle.labelColor
                                            opacity: model.error3D
                                                     || model.error2D
                                                     ? 1 : 0.62
                                            Layout.fillWidth: true
                                            elide: Text.ElideMiddle
                                        }
                                    }
                                }
                            }
                        }

                        MonitorPanel {
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

                                delegate: Rectangle {
                                    width: ListView.view.width
                                    height: 34
                                    color: index % 2
                                           ? coreStyle.panelAlternateColor
                                           : "transparent"
                                    radius: 3

                                    RowLayout {
                                        anchors.fill: parent
                                        anchors.leftMargin: 7
                                        anchors.rightMargin: 7

                                        StatusDot { active: model.online }
                                        Label {
                                            text: model.serviceName
                                            color: coreStyle.titleColor
                                            font.bold: true
                                            Layout.fillWidth: true
                                            elide: Text.ElideRight
                                        }
                                        Label {
                                            text: model.hasPort
                                                  ? ":" + model.port : ""
                                            color: coreStyle.labelColor
                                            opacity: 0.65
                                        }
                                        Label {
                                            text: model.online
                                                  ? "运行中" : "未运行"
                                            color: model.online
                                                   ? "#4CAF69"
                                                   : "#EF5350"
                                        }
                                    }
                                }
                            }
                        }

                        MonitorPanel {
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

                                delegate: Rectangle {
                                    width: ListView.view.width
                                    height: 42
                                    color: index % 2
                                           ? coreStyle.panelAlternateColor
                                           : "transparent"
                                    radius: 3

                                    RowLayout {
                                        anchors.fill: parent
                                        anchors.leftMargin: 7
                                        anchors.rightMargin: 7

                                        StatusDot { active: model.isUp }
                                        ColumnLayout {
                                            spacing: 0
                                            Layout.fillWidth: true
                                            Label {
                                                text: model.adapterName
                                                color: coreStyle.titleColor
                                                font.bold: true
                                                Layout.fillWidth: true
                                                elide: Text.ElideRight
                                            }
                                            Label {
                                                text: (model.ipv4 || "-")
                                                      + "  "
                                                      + model.speedMbps
                                                      + " Mbps"
                                                color: coreStyle.labelColor
                                                opacity: 0.62
                                                font.pixelSize: 11
                                            }
                                        }
                                        Label {
                                            text: "↓"
                                                  + root.formatRate(
                                                      model.rxBytesPerSecond)
                                                  + "  ↑"
                                                  + root.formatRate(
                                                      model.txBytesPerSecond)
                                            color: coreStyle.labelColor
                                        }
                                    }
                                }
                            }
                        }
                    }
                }
            }

            Item {
                MonitorPanel {
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

                        delegate: Rectangle {
                            visible: model.cap3D
                            width: GridView.view.cellWidth - 10
                            height: GridView.view.cellHeight - 10
                            color: coreStyle.panelAlternateColor
                            border.color: model.camera3DOk
                                          ? "#3F8F63" : "#A85A50"
                            radius: coreStyle.controlRadius

                            ColumnLayout {
                                anchors.fill: parent
                                anchors.margins: 10
                                spacing: 5

                                RowLayout {
                                    Layout.fillWidth: true
                                    StatusDot {
                                        active: model.camera3DOk
                                    }
                                    Label {
                                        text: model.cameraKey + "  "
                                              + model.cameraName
                                        color: coreStyle.titleColor
                                        font.bold: true
                                        font.pixelSize: 15
                                        Layout.fillWidth: true
                                        elide: Text.ElideRight
                                    }
                                    Label {
                                        text: model.camera3DAcquiring
                                              ? "采集中"
                                              : model.camera3DConnected
                                                ? "已连接" : "离线"
                                        color: model.camera3DOk
                                               ? "#4CAF69"
                                               : "#EF5350"
                                        font.bold: true
                                    }
                                }

                                Label {
                                    text: "SN: " + (model.sn || "-")
                                          + "    最近帧: "
                                          + (model.hasFrame3D
                                             ? root.formatAge(
                                                   model.lastFrameAge3D)
                                             : "-")
                                    color: coreStyle.labelColor
                                    opacity: 0.72
                                }

                                Rectangle {
                                    Layout.fillWidth: true
                                    Layout.preferredHeight: 48
                                    color: coreStyle.panelElevatedColor
                                    radius: 4

                                    RowLayout {
                                        anchors.fill: parent
                                        anchors.margins: 8
                                        Label {
                                            text: "设备温度"
                                            color: coreStyle.labelColor
                                            Layout.fillWidth: true
                                        }
                                        Label {
                                            text: root.formatTemperature(
                                                      model.temperature3DAvailable,
                                                      model.temperature3D,
                                                      model.temperature3DStale)
                                            color: root.temperatureColor(
                                                       model.temperature3DAvailable,
                                                       model.temperature3D,
                                                       model.temperature3DStale)
                                            font.pixelSize: 19
                                            font.bold: true
                                        }
                                    }
                                }

                                Label {
                                    text: "启动失败: "
                                          + model.startFailures
                                          + "    最后动作: "
                                          + (model.last3DAction || "-")
                                    color: coreStyle.labelColor
                                    opacity: 0.72
                                    Layout.fillWidth: true
                                    elide: Text.ElideRight
                                }

                                Label {
                                    text: model.error3D
                                          || model.temperature3DError
                                          || "运行正常"
                                    color: model.error3D
                                           ? "#EF5350"
                                           : coreStyle.labelColor
                                    Layout.fillWidth: true
                                    elide: Text.ElideMiddle
                                }

                                RowLayout {
                                    Layout.fillWidth: true
                                    Item { Layout.fillWidth: true }
                                    Button {
                                        text: "重连 3D"
                                        enabled: !model.busy
                                        onClicked: root.runCameraAction(
                                                       index, "reconnect3d")
                                    }
                                    Button {
                                        text: "复位 3D"
                                        enabled: !model.busy
                                        onClicked:
                                            root.confirmCameraReset(index)
                                    }
                                }
                            }
                        }
                    }
                }
            }

            Item {
                MonitorPanel {
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

                        delegate: Rectangle {
                            visible: model.cap2D
                            width: GridView.view.cellWidth - 10
                            height: GridView.view.cellHeight - 10
                            color: coreStyle.panelAlternateColor
                            border.color: model.camera2DOk
                                          ? "#3F8F63" : "#A85A50"
                            radius: coreStyle.controlRadius

                            ColumnLayout {
                                anchors.fill: parent
                                anchors.margins: 10
                                spacing: 5

                                RowLayout {
                                    Layout.fillWidth: true
                                    StatusDot {
                                        active: model.camera2DOk
                                    }
                                    Label {
                                        text: model.cameraKey + "  "
                                              + model.cameraName
                                        color: coreStyle.titleColor
                                        font.bold: true
                                        font.pixelSize: 15
                                        Layout.fillWidth: true
                                        elide: Text.ElideRight
                                    }
                                    Label {
                                        text: model.camera2DConnected
                                              ? (model.state2D
                                                 === "waiting_trigger"
                                                 ? "等待触发" : "采集中")
                                              : "离线"
                                        color: model.camera2DOk
                                               ? "#4CAF69"
                                               : "#EF5350"
                                        font.bold: true
                                    }
                                }

                                Label {
                                    text: "最近帧: "
                                          + (model.hasFrame2D
                                             ? root.formatAge(
                                                   model.lastFrameAge2D)
                                             : "-")
                                          + "    分辨率: "
                                          + (model.width2D > 0
                                             ? model.width2D + " × "
                                               + model.height2D
                                             : "-")
                                    color: coreStyle.labelColor
                                    opacity: 0.72
                                }

                                Rectangle {
                                    Layout.fillWidth: true
                                    Layout.preferredHeight: 48
                                    color: coreStyle.panelElevatedColor
                                    radius: 4

                                    RowLayout {
                                        anchors.fill: parent
                                        anchors.margins: 8
                                        Label {
                                            text: "设备温度"
                                            color: coreStyle.labelColor
                                            Layout.fillWidth: true
                                        }
                                        Label {
                                            text: root.formatTemperature(
                                                      model.temperature2DAvailable,
                                                      model.temperature2D,
                                                      model.temperature2DStale)
                                            color: root.temperatureColor(
                                                       model.temperature2DAvailable,
                                                       model.temperature2D,
                                                       model.temperature2DStale)
                                            font.pixelSize: 19
                                            font.bold: true
                                        }
                                    }
                                }

                                GridLayout {
                                    Layout.fillWidth: true
                                    columns: 2
                                    columnSpacing: 12
                                    rowSpacing: 2

                                    Label {
                                        text: "帧号 "
                                              + model.frameId2D
                                        color: coreStyle.labelColor
                                    }
                                    Label {
                                        text: "空帧 "
                                              + model.emptyFrames2D
                                        color: coreStyle.labelColor
                                    }
                                    Label {
                                        text: "错误 "
                                              + model.frameErrors2D
                                              + " / 丢弃 "
                                              + model.droppedFrames2D
                                        color: coreStyle.labelColor
                                    }
                                    Label {
                                        text: "队列 "
                                              + model.queueSize2D
                                              + " / 重连 "
                                              + model.connectAttempts2D
                                        color: coreStyle.labelColor
                                    }
                                    Label {
                                        text: "曝光 "
                                              + (model.exposureTime2D
                                                 === null
                                                 ? "-"
                                                 : model.exposureTime2D)
                                        color: coreStyle.labelColor
                                    }
                                    Label {
                                        text: "增益 "
                                              + (model.gain2D === null
                                                 ? "-" : model.gain2D)
                                        color: coreStyle.labelColor
                                    }
                                }

                                Label {
                                    text: model.error2D
                                          || root.temperatureAvailabilityText(
                                              model.temperature2DError)
                                          || "运行正常"
                                    color: model.error2D
                                           ? "#EF5350"
                                           : coreStyle.labelColor
                                    Layout.fillWidth: true
                                    elide: Text.ElideMiddle
                                }

                                RowLayout {
                                    Layout.fillWidth: true
                                    Item { Layout.fillWidth: true }
                                    Button {
                                        text: "重连 2D"
                                        enabled: !model.busy
                                        onClicked: root.runCameraAction(
                                                       index, "reconnect2d")
                                    }
                                }
                            }
                        }
                    }
                }
            }

            Item {
                MonitorPanel {
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

                        delegate: Rectangle {
                            width: GridView.view.cellWidth - 10
                            height: GridView.view.cellHeight - 10
                            color: coreStyle.panelAlternateColor
                            border.color: model.isUp
                                          ? "#3F8F63" : "#6B7785"
                            radius: coreStyle.controlRadius

                            ColumnLayout {
                                anchors.fill: parent
                                anchors.margins: 10
                                spacing: 5

                                RowLayout {
                                    Layout.fillWidth: true
                                    StatusDot { active: model.isUp }
                                    Label {
                                        text: model.adapterName
                                        color: coreStyle.titleColor
                                        font.bold: true
                                        font.pixelSize: 15
                                        Layout.fillWidth: true
                                        elide: Text.ElideRight
                                    }
                                    Label {
                                        text: model.isUp ? "在线" : "离线"
                                        color: model.isUp
                                               ? "#4CAF69" : "#90A4AE"
                                        font.bold: true
                                    }
                                }

                                Label {
                                    text: "IPv4: " + (model.ipv4 || "-")
                                    color: coreStyle.labelColor
                                    Layout.fillWidth: true
                                    elide: Text.ElideMiddle
                                }
                                Label {
                                    text: "MAC: " + (model.mac || "-")
                                          + "    链路: "
                                          + (model.speedMbps > 0
                                             ? model.speedMbps
                                               + " Mbps" : "-")
                                          + "    MTU: " + model.mtu
                                    color: coreStyle.labelColor
                                    opacity: 0.72
                                }
                                Label {
                                    text: "↓ "
                                          + root.formatRate(
                                              model.rxBytesPerSecond)
                                          + "    ↑ "
                                          + root.formatRate(
                                              model.txBytesPerSecond)
                                          + "    错误 " + model.errors
                                          + " / 丢包 " + model.drops
                                    color: coreStyle.labelColor
                                }
                                Label {
                                    text: "累计接收 "
                                          + root.formatBytes(
                                              model.bytesReceived)
                                          + " / 发送 "
                                          + root.formatBytes(
                                              model.bytesSent)
                                    color: coreStyle.labelColor
                                    opacity: 0.62
                                }

                                RowLayout {
                                    Layout.fillWidth: true
                                    Label {
                                        text: model.canControl
                                              ? ""
                                              : root.networkControlReason(
                                                  model.controlReason)
                                        color: "#FFB74D"
                                        Layout.fillWidth: true
                                        elide: Text.ElideRight
                                    }
                                    Button {
                                        text: model.isUp ? "禁用" : "启用"
                                        enabled: model.canControl
                                                 && !model.busy
                                        onClicked:
                                            root.confirmNetworkAction(
                                                index,
                                                model.isUp
                                                ? "disable" : "enable")
                                    }
                                    Button {
                                        text: "重启"
                                        visible: model.isUp
                                        enabled: model.canControl
                                                 && !model.busy
                                        onClicked:
                                            root.confirmNetworkAction(
                                                index, "restart")
                                    }
                                }
                            }
                        }
                    }
                }
            }

            Item {
                MonitorPanel {
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

                        delegate: Rectangle {
                            width: GridView.view.cellWidth - 10
                            height: GridView.view.cellHeight - 10
                            color: coreStyle.panelAlternateColor
                            border.color: model.online
                                          ? "#3F8F63" : "#A85A50"
                            radius: coreStyle.controlRadius

                            ColumnLayout {
                                anchors.fill: parent
                                anchors.margins: 10
                                spacing: 5

                                RowLayout {
                                    Layout.fillWidth: true
                                    StatusDot { active: model.online }
                                    Label {
                                        text: model.serviceName
                                        color: coreStyle.titleColor
                                        font.bold: true
                                        font.pixelSize: 15
                                        Layout.fillWidth: true
                                        elide: Text.ElideRight
                                    }
                                    Rectangle {
                                        implicitWidth: categoryText.width + 12
                                        implicitHeight: 23
                                        color: coreStyle.panelElevatedColor
                                        radius: 3
                                        Label {
                                            id: categoryText
                                            anchors.centerIn: parent
                                            text: model.category
                                            color: coreStyle.labelColor
                                            font.pixelSize: 11
                                        }
                                    }
                                    Label {
                                        text: model.online
                                              ? "运行中" : model.stateText
                                        color: model.online
                                               ? "#4CAF69" : "#EF5350"
                                        font.bold: true
                                    }
                                }

                                Label {
                                    text: model.hasPort
                                          ? "端点 "
                                            + model.host + ":"
                                            + model.port
                                          : "后台进程"
                                    color: coreStyle.labelColor
                                }
                                Label {
                                    text: "PID "
                                          + (model.hasPid
                                             ? model.pid : "-")
                                          + "    "
                                          + (model.processName || "-")
                                    color: coreStyle.labelColor
                                    opacity: 0.72
                                }
                                Label {
                                    text: "运行 "
                                          + (model.hasUptime
                                             ? root.formatDuration(
                                                   model.uptimeSeconds)
                                             : "-")
                                          + "    内存 "
                                          + root.formatBytes(
                                              model.memoryBytes)
                                    color: coreStyle.labelColor
                                    opacity: 0.72
                                }
                                RowLayout {
                                    Layout.fillWidth: true
                                    Label {
                                        text: model.message
                                              || model.commandLine
                                              || "-"
                                        color: model.online
                                               ? coreStyle.labelColor
                                               : "#EF5350"
                                        Layout.fillWidth: true
                                        elide: Text.ElideMiddle
                                    }
                                    Button {
                                        visible: model.canRestart
                                        enabled: !model.busy
                                        text: model.busy ? "重启中" : "重启"
                                        Material.background: Material.Orange
                                        onClicked: root.confirmServiceRestart(index)
                                    }
                                }
                            }
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
            color: coreStyle.labelColor
            wrapMode: Text.WordWrap
            padding: 18
        }

        standardButtons: Dialog.Ok | Dialog.Cancel
        onAccepted: {
            if (targetKind === "camera") {
                root.runCameraAction(targetIndex, targetAction)
            } else if (targetKind === "network") {
                root.runNetworkAction(targetIndex, targetAction)
            } else if (targetKind === "service") {
                root.runServiceRestart(targetIndex)
            }
        }
    }

    component StatusDot: Rectangle {
        property bool active: false
        implicitWidth: 10
        implicitHeight: 10
        radius: 5
        color: active ? "#4CAF69" : "#EF5350"
    }

    component CompactSummary: RowLayout {
        id: compactSummary

        property string label: ""
        property string value: ""
        property bool healthy: false

        spacing: 5
        StatusDot { active: compactSummary.healthy }
        Label {
            text: compactSummary.label
            color: coreStyle.labelColor
        }
        Label {
            text: compactSummary.value
            color: compactSummary.healthy ? "#4CAF69" : "#FFB74D"
            font.bold: true
        }
    }

    component KpiCard: Rectangle {
        id: kpiCard

        property string title: ""
        property string value: ""
        property string detail: ""
        property color accent: "#4CAF69"

        Layout.fillWidth: true
        Layout.preferredHeight: 72
        color: coreStyle.panelAlternateColor
        border.color: accent
        border.width: 1
        radius: coreStyle.controlRadius

        RowLayout {
            anchors.fill: parent
            anchors.margins: 10
            Rectangle {
                Layout.preferredWidth: 4
                Layout.fillHeight: true
                color: kpiCard.accent
                radius: 2
            }
            ColumnLayout {
                Layout.fillWidth: true
                spacing: 1
                Label {
                    text: kpiCard.title
                    color: coreStyle.labelColor
                    opacity: 0.72
                }
                Label {
                    text: kpiCard.value
                    color: kpiCard.accent
                    font.pixelSize: 20
                    font.bold: true
                }
                Label {
                    text: kpiCard.detail
                    color: coreStyle.labelColor
                    opacity: 0.58
                    font.pixelSize: 11
                }
            }
        }
    }

    component MonitorPanel: Rectangle {
        id: panel
        property string panelTitle: ""
        property string panelCaption: ""
        default property alias content: panelBody.data

        color: coreStyle.panelElevatedColor
        border.color: coreStyle.headerBorderColor
        border.width: 1
        radius: coreStyle.controlRadius

        ColumnLayout {
            anchors.fill: parent
            anchors.margins: 9
            spacing: 6

            RowLayout {
                Layout.fillWidth: true
                Label {
                    text: panel.panelTitle
                    color: coreStyle.titleColor
                    font.bold: true
                    font.pixelSize: 15
                }
                Label {
                    text: panel.panelCaption
                    color: coreStyle.labelColor
                    opacity: 0.58
                    Layout.fillWidth: true
                    elide: Text.ElideRight
                }
            }

            Item {
                id: panelBody
                Layout.fillWidth: true
                Layout.fillHeight: true
            }
        }
    }
}
