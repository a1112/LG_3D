pragma ComponentBehavior: Bound
import QtQuick 2.15
import QtQuick.Controls
import QtQuick.Controls.Material
import QtQuick.Layouts
Item {
    id: root

    required property var apiClient
    required property var modelStore
    required property var style
    required property var scriptLauncher

    property int selectedPort: 0
    property int alarmLevel: 0
    property bool pollingEnabled: true
    property bool requestRunning: false
    property var pendingPorts: []
    property int pollGeneration: 0
    property ListModel netModel: ListModel {}

    function init() {
        root.netModel.clear()
        root.netModel.append({
                            titleText: "核心 API",
                            valueText: "--",
                            level: 1,
                            msg: "卷材、报警与配置接口",
                            port: root.apiClient.apiConfig.activeApiPort
                        }
                    )
        root.netModel.append({
                            titleText: "图像服务",
                            valueText: "--",
                            level: 1,
                            port: root.apiClient.apiConfig.activeImageServerPort,
                            msg: "二维图像与渲染接口"
                        }
                        )
        root.netModel.append({
                            titleText: "2D 算法",
                            valueText: "--",
                            level: 1,
                            port: root.apiClient.apiConfig.alg2dPort,
                            msg: "二维检测接口"
                        })
    }

    function updatePortStatus(portNumber, delayValue, ok) {
        for (let i = 0; i < root.netModel.count; ++i) {
            let item = root.netModel.get(i)
            if (Number(item.port) !== Number(portNumber)) {
                continue
            }
            root.netModel.setProperty(
                        i, "valueText",
                        ok ? Number(delayValue).toFixed(0) + " ms"
                           : qsTr("连接错误"))
            root.netModel.setProperty(i, "level", ok ? 0 : 3)
            root.modelStore.coreGlobalError.setStateLevel(
                        "网络", i, ok ? 0 : 3)
        }
    }

    function pollNextPort(generation) {
        if (generation !== root.pollGeneration || !root.pollingEnabled) {
            root.requestRunning = false
            return
        }
        if (root.pendingPorts.length === 0) {
            root.requestRunning = false
            return
        }
        let portNumber = root.pendingPorts.shift()
        root.apiClient.__getDelay__(portNumber, function(delayValue) {
            if (generation !== root.pollGeneration) {
                return
            }
            root.updatePortStatus(portNumber, delayValue, true)
            root.pollNextPort(generation)
        }, function() {
            if (generation !== root.pollGeneration) {
                return
            }
            root.updatePortStatus(portNumber, 0, false)
            root.pollNextPort(generation)
        })
    }

    function refresh() {
        if (root.requestRunning || !root.pollingEnabled) {
            return
        }
        let uniquePorts = []
        for (let i = 0; i < root.netModel.count; ++i) {
            let portNumber = Number(root.netModel.get(i).port)
            if (isFinite(portNumber) && uniquePorts.indexOf(portNumber) < 0) {
                uniquePorts.push(portNumber)
            }
        }
        if (uniquePorts.length === 0) {
            return
        }
        root.requestRunning = true
        root.pendingPorts = uniquePorts
        const generation = ++root.pollGeneration
        root.pollNextPort(generation)
    }

    onPollingEnabledChanged: {
        if (!root.pollingEnabled) {
            root.pollGeneration++
            root.pendingPorts = []
            root.requestRunning = false
        }
    }

    Timer {
        interval: 10000
        repeat: true
        triggeredOnStart: true
        running: root.visible && root.pollingEnabled
        onTriggered: root.refresh()
    }

    Component.onCompleted: init()


    ColumnLayout{
        anchors.fill: parent
        Item{
        Layout.fillWidth: true
        height:wl_id.height

        Row{
            spacing: 10
                        anchors.centerIn: parent
        Label{
            id:wl_id
            text:"网络状态"
            font.pointSize: 18
            font.bold: true
            color: root.style.titleColor
            font.family: "Microsoft YaHei"
            Layout.alignment: Qt.AlignHCenter
        }
        ItemDelegate{
            height: parent.height
            width: height
            ToolTip.visible:hovered
            ToolTip.text: "远程到服务器"
            onClicked:{
                root.scriptLauncher.launchScript(
                            "/c start /wait mstsc /v "
                            + root.apiClient.apiConfig.hostname)
            }
            Image {
                width: parent.width
                height: parent.height
                id: image
                source: root.style.getIcon("uploading")
            }
        }


        }
        // Label{
        //     anchors.right: parent.right
        //     text:"延时："+api.delay+"  "
        //     font.pointSize: 12
        //     color: api.connectColor
        //     font.family: "Microsoft YaHei"
        // }

        }
        Item{
            id:body
            Layout.fillWidth: true
            Layout.fillHeight: true
            GridView{
                id: netGrid
                anchors.fill: parent
                model: root.netModel
                cellWidth: parent.width / 2-1
                cellHeight: 25
                reuseItems: true
                delegate: AlarmItemNetItem {
                    id: netDelegate
                    style: root.style
                    width: netGrid.cellWidth
                    height:25

                    TapHandler {
                        acceptedButtons: Qt.RightButton
                        onTapped: {
                            root.selectedPort = netDelegate.port
                            netMenu.popup()
                        }
                    }
                }
            }


        }
    }

    Menu{
        id:netMenu
        MenuItem{
            text:"打开接口文档"
            onTriggered:{
                root.apiClient.openApi(root.selectedPort)
            }
        }
    }

}
