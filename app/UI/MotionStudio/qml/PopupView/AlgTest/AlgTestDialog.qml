import QtQuick
import QtQuick.Controls
import QtQuick.Controls.Material
import QtQuick.Layouts
import QtQuick.Dialogs
import QtWebSockets

import "../Base"
import "../../Labels"
import "../../Input"
import "../../Pages/Header"

ApplicationWindow {
    id: root


    width: 900
    height: 640
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
        if (!api || !api.getAlgModels) {
            statusMessage = qsTr("缺少算法模型接口")
            return
        }
        loadingModels = true
        statusMessage = qsTr("正在获取模型列表...")
        api.getAlgModels(function(resp) {
            loadingModels = false
            var parsed = []
            try {
                var data = JSON.parse(resp)
                parsed = data.models || []
            } catch (e) {
                console.warn("getAlgModels parse error", e)
            }
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
        if (!api || !api.getAlgTestWsUrl)
            return ""
        return api.getAlgTestWsUrl()
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
        api.startAlgTest(payload, function(resp) {
            var js = {}
            try { js = JSON.parse(resp) } catch(e) { js = {} }
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
        if (api && api.stopAlgTest) {
            api.stopAlgTest({task_id: currentTaskId}, function(){ appendLog(qsTr("服务端已确认停止")) }, function(err){ appendLog(qsTr("停止失败: %1").arg(err)) })
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
        logModel.append({text: stamp + "  " + msg})
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

    FileDialog {
        id: targetFolderDialog
        title: qsTr("选择目标文件夹")
        fileMode: FileDialog.OpenDirectory
        onAccepted: {
            if (selectedFiles && selectedFiles.length > 0)
                targetFolder = cleanFolderPath(selectedFiles[0])
        }
    }

    FileDialog {
        id: outputFolderDialog
        title: qsTr("选择输出文件夹")
        fileMode: FileDialog.OpenDirectory
        onAccepted: {
            if (selectedFiles && selectedFiles.length > 0)
                outputFolder = cleanFolderPath(selectedFiles[0])
        }
    }

    WebSocket {
        id: progressSocket
        active: false
        url: ""
        onStatusChanged: {
            if (status === WebSocket.Error) {
                appendLog(qsTr("进度连接错误: %1").arg(errorString))
                statusMessage = errorString
            } else if (status === WebSocket.Closed && running) {
                appendLog(qsTr("进度连接已关闭"))
            }
        }
        onTextMessageReceived: function(message) {
            var js = {}
            try { js = JSON.parse(message) } catch(e) { js = {message: message} }
            if (js.task_id && !currentTaskId)
                currentTaskId = js.task_id
            if (js.speed !== undefined)
                progressSpeed = js.speed
            if (js.done !== undefined)
                processedCount = js.done
            if (js.total !== undefined)
                totalCount = js.total
            if (js.eta !== undefined)
                etaSeconds = js.eta || 0
            if (js.message)
                appendLog(js.message)
            if (js.status)
                statusMessage = js.status
            if (js.finished) {
                running = false
                progressSocket.active = false
                if (js.summary)
                    appendLog(qsTr("任务完成"))
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
                displayText: selectedModel ? selectedModel.display_name : qsTr("请选择模型")
                enabled: !loadingModels
                delegate: ItemDelegate {
                    required property int index
                    width: modelCombo.width
                    required property var modelData
                    text: modelData.display_name || modelData.name
                    onClicked: {
                        modelCombo.currentIndex = index
                        selectedModel = modelData
                        modelCombo.popup.close()
                    }
                }
            }
            RowLayout {
                Button {
                    text: qsTr("刷新")
                    enabled: !loadingModels
                    onClicked: refreshModels()
                }
                BusyIndicator {
                    running: loadingModels
                    visible: loadingModels
                    width: 20
                    height: 20
                }
            }

            Label { text: qsTr("目标文件夹"); Layout.alignment: Qt.AlignVCenter }
            TextField {
                Layout.fillWidth: true
                text: targetFolder
                placeholderText: qsTr("递归扫描的图像根目录")
                onEditingFinished: targetFolder = text.trim()
            }
            Button {
                text: qsTr("选择")
                onClicked: targetFolderDialog.open()
            }

            Label { text: qsTr("输出文件夹"); Layout.alignment: Qt.AlignVCenter }
            TextField {
                Layout.fillWidth: true
                text: outputFolder
                placeholderText: qsTr("保存检测结果的目录")
                onEditingFinished: outputFolder = text.trim()
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
                    value: threshold * 100
                    stepSize: 1
                    onValueChanged: threshold = value / 100
                }
                TextField {
                    width: 60
                    text: threshold.toFixed(2)
                    inputMethodHints: Qt.ImhFormattedNumbersOnly
                    onEditingFinished: {
                        var val = parseFloat(text)
                        if (isNaN(val))
                            val = 0.4
                        val = Math.max(0.01, Math.min(0.99, val))
                        threshold = val
                        text = threshold.toFixed(2)
                        thresholdSlider.value = threshold * 100
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
                    checked: mode === "copy"
                    onClicked: mode = "copy"
                    ButtonGroup.group: modeGroup
                }
                RadioButton {
                    text: qsTr("移动")
                    checked: mode === "move"
                    onClicked: mode = "move"
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
                    checked: optionClassify
                    onToggled: optionClassify = checked
                }
                CheckBox {
                    text: qsTr("保存标注文件")
                    enabled: !selectedModel || selectedModel.type !== "classifier"
                    checked: optionSaveLabel && enabled
                    onToggled: optionSaveLabel = enabled && checked
                }
            }
        }

        RowLayout {
            Layout.fillWidth: true
            spacing: 10
            Button {
                text: running ? qsTr("执行中...") : qsTr("开始测试")
                enabled: !running
                onClicked: startTest()
            }
            Button {
                text: qsTr("停止")
                enabled: running
                onClicked: stopTest()
            }
            Button {
                text: qsTr("关闭")
                onClicked: root.close()
            }
            Item { Layout.fillWidth: true }
            Label {
                text: statusMessage
                color: Material.color(Material.LightBlue)
                elide: Text.ElideRight
                Layout.preferredWidth: 320
            }
        }

        ProgressBar {
            Layout.fillWidth: true
            from: 0
            to: Math.max(totalCount, 1)
            value: processedCount
        }

        RowLayout {
            Layout.fillWidth: true
            spacing: 20
            Label { text: qsTr("%1 / %2 张").arg(processedCount).arg(totalCount || qsTr("未知")) }
            Label { text: qsTr("速度 %1 张/秒").arg(progressSpeed.toFixed(2)) }
            Label { text: qsTr("预计 %1").arg(formatEta(etaSeconds)) }
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
                    width: logList.width - 12
                    text: model.text
                    color: "#E0E0E0"
                    wrapMode: Text.WrapAnywhere
                }
            }
        }
    }
}
