pragma ComponentBehavior: Bound

import QtQuick
import QtQuick.Controls
import QtQuick.Controls.Material
import QtQuick.Layouts
import QtQuick.Dialogs
import QtWebSockets

import "../../Core/JsonUtils.js" as JsonUtils

ApplicationWindow {
    id: root

    required property var apiClient
    required property var adaptiveMetrics
    required property var style

    width: adaptiveMetrics.boundedWidth(900, 680, 1100)
    height: adaptiveMetrics.boundedHeight(640, 500, 820)
    property var modelList: []
    property var selectedModel: null
    property string targetFolder: ""
    property string outputFolder: ""
    property real threshold: 0.4
    property string mode: "copy"
    property bool optionClassify: true
    property bool optionSaveLabel: false
    property bool running: false
    property bool loadingModels: false
    property int processedCount: 0
    property int totalCount: 0
    property real progressSpeed: 0
    property real etaSeconds: 0
    property string statusMessage: ""
    property string currentTaskId: ""

    function openDialog() {
        visible=true
        if (!modelList.length) {
            refreshModels()
        }
    }



    function refreshModels() {
        if (!root.apiClient || !root.apiClient.getAlgModels) {
            statusMessage = qsTr("缺少算法模型接口")
            return
        }
        loadingModels = true
        statusMessage = qsTr("正在获取模型列表...")
        root.apiClient.getAlgModels(function(resp) {
            loadingModels = false
            var parsed = []
            var data = JsonUtils.parse(resp, {}, "algorithm model list")
            parsed = data.models || []
            modelList = parsed
            if (parsed.length > 0) {
                selectedModel = parsed[0]
                modelCombo.currentIndex = 0
                statusMessage = qsTr("可用模型: %1").arg(parsed.length)
            } else {
                modelCombo.currentIndex = -1
                selectedModel = null
                statusMessage = qsTr("未找到模型")
            }
        }, function(err) {
            loadingModels = false
            statusMessage = qsTr("模型列表获取失败")
            console.warn("getAlgModels error", err)
        })
    }

    function cleanFolderPath(url) {
        if (!url)
            return ""
        var str = url.toString ? url.toString() : url
        return decodeURIComponent(str.replace("file:///", "").replace("file://", ""))
    }

    function validateInputs() {
        if (!selectedModel) {
            statusMessage = qsTr("请选择模型")
            return false
        }
        if (!targetFolder) {
            statusMessage = qsTr("请选择目标文件夹")
            return false
        }
        if (!outputFolder) {
            statusMessage = qsTr("请选择输出文件夹")
            return false
        }
        return true
    }

    function progressUrl() {
        if (!root.apiClient || !root.apiClient.getAlgTestWsUrl)
            return ""
        return root.apiClient.getAlgTestWsUrl()
    }

    function startTest() {
        if (running)
            return
        if (!validateInputs())
            return
        running = true
        processedCount = 0
        totalCount = 0
        progressSpeed = 0
        etaSeconds = 0
        currentTaskId = ""
        statusMessage = qsTr("正在启动算法测试...")
        logModel.clear()
        appendLog(qsTr("开始执行: %1").arg(selectedModel.display_name || selectedModel.name))
        openProgressSocket()
        var payload = {
            model: selectedModel.name,
            target: targetFolder,
            output: outputFolder,
            threshold: threshold,
            mode: mode,
            options: {
                classify_save: optionClassify,
                save_label: optionSaveLabel
            }
        }
        root.apiClient.startAlgTest(payload, function(resp) {
            var js = JsonUtils.parse(resp, {}, "algorithm test start")
            if (js.task_id)
                currentTaskId = js.task_id
            statusMessage = qsTr("任务已启动")
        }, function(err) {
            running = false
            progressSocket.active = false
            statusMessage = qsTr("启动失败")
            appendLog(qsTr("启动失败: %1").arg(err))
        })
    }

    function stopTest() {
        if (!running) {
            progressSocket.active = false
            return
        }
        running = false
        statusMessage = qsTr("已请求停止")
        progressSocket.active = false
        if (root.apiClient && root.apiClient.stopAlgTest) {
            root.apiClient.stopAlgTest(
                        {task_id: root.currentTaskId},
                        function() {
                            root.appendLog(qsTr("服务端已确认停止"))
                        },
                        function(err) {
                            root.appendLog(qsTr("停止失败: %1").arg(err))
                        })
        }
    }

    function openProgressSocket() {
        var url = progressUrl()
        if (!url) {
            appendLog(qsTr("WebSocket 地址无效"))
            return
        }
        progressSocket.active = false
        progressSocket.url = url
        progressSocket.active = true
    }

    function appendLog(msg) {
        var stamp = Qt.formatDateTime(new Date(), "hh:mm:ss")
        logModel.append({logText: stamp + "  " + msg})
        if (logModel.count > 200)
            logModel.remove(0, logModel.count - 200)
    }

    function formatEta(seconds) {
        if (!seconds || seconds <= 0)
            return qsTr("计算中")
        if (seconds >= 3600) {
            var h = Math.floor(seconds / 3600)
            var m = Math.floor((seconds % 3600) / 60)
            return qsTr("%1小时%2分").arg(h).arg(m)
        }
        if (seconds >= 60) {
            var mins = Math.floor(seconds / 60)
            var secs = Math.floor(seconds % 60)
            return qsTr("%1分%2秒").arg(mins).arg(secs)
        }
        return qsTr("%1秒").arg(Math.floor(seconds))
    }

    ListModel { id: logModel }

    FolderDialog {
        id: targetFolderDialog
        title: qsTr("选择目标文件夹")
        onAccepted: {
            root.targetFolder = root.cleanFolderPath(selectedFolder)
        }
    }

    FolderDialog {
        id: outputFolderDialog
        title: qsTr("选择输出文件夹")
        onAccepted: {
            root.outputFolder = root.cleanFolderPath(selectedFolder)
        }
    }

    WebSocket {
        id: progressSocket
        active: false
        url: ""
        onStatusChanged: {
            if (status === WebSocket.Error) {
                root.appendLog(qsTr("进度连接错误: %1").arg(errorString))
                root.statusMessage = errorString
            } else if (status === WebSocket.Closed && root.running) {
                root.appendLog(qsTr("进度连接已关闭"))
            }
        }
        onTextMessageReceived: function(message) {
            var js = JsonUtils.parse(message, {message: message},
                                     "algorithm test progress")
            if (js.task_id && !root.currentTaskId)
                root.currentTaskId = js.task_id
            if (js.speed !== undefined)
                root.progressSpeed = js.speed
            if (js.done !== undefined)
                root.processedCount = js.done
            if (js.total !== undefined)
                root.totalCount = js.total
            if (js.eta !== undefined)
                root.etaSeconds = js.eta || 0
            if (js.message)
                root.appendLog(js.message)
            if (js.status)
                root.statusMessage = js.status
            if (js.finished) {
                root.running = false
                progressSocket.active = false
                if (js.summary)
                    root.appendLog(qsTr("任务完成"))
            }
        }
    }

    onSelectedModelChanged: {
        if (selectedModel && selectedModel.type === "classifier" && optionSaveLabel) {
            optionSaveLabel = false
        }
    }

    ColumnLayout {
        anchors.fill: parent
        spacing: 12

        Label {
            text: qsTr("算法测试")
            font.bold: true
            font.pointSize: 20
            Layout.alignment: Qt.AlignHCenter
        }

        GridLayout {
            Layout.fillWidth: true
            columns: 3
            columnSpacing: 12
            rowSpacing: 10

            Label { text: qsTr("模型"); Layout.alignment: Qt.AlignVCenter }
            ComboBox {
                id: modelCombo
                Layout.fillWidth: true
                model: root.modelList
                textRole: "display_name"
                displayText: root.selectedModel
                             ? root.selectedModel.display_name
                             : qsTr("请选择模型")
                enabled: !root.loadingModels
                delegate: ItemDelegate {
                    required property int index
                    width: modelCombo.width
                    required property var modelData
                    text: modelData.display_name || modelData.name
                    onClicked: {
                        modelCombo.currentIndex = index
                        root.selectedModel = modelData
                        modelCombo.popup.close()
                    }
                }
            }
            RowLayout {
                Button {
                    text: qsTr("刷新")
                    enabled: !root.loadingModels
                    onClicked: root.refreshModels()
                }
                BusyIndicator {
                    running: root.loadingModels
                    visible: root.loadingModels
                    width: 20
                    height: 20
                }
            }

            Label { text: qsTr("目标文件夹"); Layout.alignment: Qt.AlignVCenter }
            TextField {
                Layout.fillWidth: true
                text: root.targetFolder
                placeholderText: qsTr("递归扫描的图像根目录")
                onEditingFinished: root.targetFolder = text.trim()
            }
            Button {
                text: qsTr("选择")
                onClicked: targetFolderDialog.open()
            }

            Label { text: qsTr("输出文件夹"); Layout.alignment: Qt.AlignVCenter }
            TextField {
                Layout.fillWidth: true
                text: root.outputFolder
                placeholderText: qsTr("保存检测结果的目录")
                onEditingFinished: root.outputFolder = text.trim()
            }
            Button {
                text: qsTr("选择")
                onClicked: outputFolderDialog.open()
            }

            Label { text: qsTr("低置信度阈值"); Layout.alignment: Qt.AlignVCenter }
            RowLayout {
                Layout.fillWidth: true
                Slider {
                    id: thresholdSlider
                    Layout.fillWidth: true
                    from: 0
                    to: 100
                    value: root.threshold * 100
                    stepSize: 1
                    onValueChanged: root.threshold = value / 100
                }
                TextField {
                    width: 60
                    text: root.threshold.toFixed(2)
                    inputMethodHints: Qt.ImhFormattedNumbersOnly
                    onEditingFinished: {
                        var val = parseFloat(text)
                        if (isNaN(val))
                            val = 0.4
                        val = Math.max(0.01, Math.min(0.99, val))
                        root.threshold = val
                        text = root.threshold.toFixed(2)
                        thresholdSlider.value = root.threshold * 100
                    }
                }
            }
            Item { width: 1; height: 1 }

            Label { text: qsTr("模式"); Layout.alignment: Qt.AlignVCenter }
            RowLayout {
                Layout.fillWidth: true
                ButtonGroup { id: modeGroup }
                RadioButton {
                    text: qsTr("复制")
                    checked: root.mode === "copy"
                    onClicked: root.mode = "copy"
                    ButtonGroup.group: modeGroup
                }
                RadioButton {
                    text: qsTr("移动")
                    checked: root.mode === "move"
                    onClicked: root.mode = "move"
                    ButtonGroup.group: modeGroup
                }
            }
            Item { width: 1; height: 1 }
        }

        Frame {
            Layout.fillWidth: true
            RowLayout {
                anchors.fill: parent
                anchors.margins: 10
                spacing: 24
                Label {
                    text: qsTr("选项")
                    color: Material.color(Material.Grey)
                }
                CheckBox {
                    text: qsTr("分类保存")
                    checked: root.optionClassify
                    onToggled: root.optionClassify = checked
                }
                CheckBox {
                    text: qsTr("保存标注文件")
                    enabled: !root.selectedModel
                             || root.selectedModel.type !== "classifier"
                    checked: root.optionSaveLabel && enabled
                    onToggled: root.optionSaveLabel = enabled && checked
                }
            }
        }

        RowLayout {
            Layout.fillWidth: true
            spacing: 10
            Button {
                text: root.running ? qsTr("执行中...") : qsTr("开始测试")
                enabled: !root.running
                onClicked: root.startTest()
            }
            Button {
                text: qsTr("停止")
                enabled: root.running
                onClicked: root.stopTest()
            }
            Button {
                text: qsTr("关闭")
                onClicked: root.close()
            }
            Item { Layout.fillWidth: true }
            Label {
                text: root.statusMessage
                color: root.style.accentColor
                elide: Text.ElideRight
                Layout.preferredWidth: 320
            }
        }

        ProgressBar {
            Layout.fillWidth: true
            from: 0
            to: Math.max(root.totalCount, 1)
            value: root.processedCount
        }

        RowLayout {
            Layout.fillWidth: true
            spacing: 20
            Label {
                text: qsTr("%1 / %2 张").arg(root.processedCount)
                      .arg(root.totalCount || qsTr("未知"))
            }
            Label {
                text: qsTr("速度 %1 张/秒").arg(root.progressSpeed.toFixed(2))
            }
            Label {
                text: qsTr("预计 %1").arg(root.formatEta(root.etaSeconds))
            }
            Item { Layout.fillWidth: true }
        }

        Frame {
            Layout.fillWidth: true
            Layout.fillHeight: true
            ListView {
                id: logList
                anchors.fill: parent
                clip: true
                model: logModel
                delegate: Text {
                    required property string logText
                    width: logList.width - 12
                    text: logText
                    color: root.style.labelColor
                    wrapMode: Text.WrapAnywhere
                }
            }
        }
    }
}
