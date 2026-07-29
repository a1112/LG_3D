pragma ComponentBehavior: Bound
import QtQuick 2.15
import QtQuick.Controls
import QtQuick.Controls.Material
import QtQuick.Layouts
Item {
    id:root
    property var glob_port
    property int alarmLevel: 0
    property bool pollingEnabled: true
    property bool requestRunning: false
    property var pendingPorts: []
    property ListModel netModel: ListModel{
    }
    function init() {
        netModel.clear()
        netModel.append({
                            titleText: "核心 API",
                            valueText: 0,
                            level: 1,
                            msg: "卷材、报警与配置接口",
                            port: api.apiConfig.activeApiPort
                        }
                    )
        netModel.append({
                            titleText: "图像服务",
                            valueText: 0,
                            level: 1,
                            port: api.apiConfig.activeImageServerPort,
                            msg: "二维图像与渲染接口"
                        }
                        )
        netModel.append(            {
                            titleText: "2D 算法",
                            valueText: 0,
                            level: 1,
                            port: api.apiConfig.alg2dPort,
                            msg: "二维检测接口"
                        })
    }

    function updatePortStatus(portNumber, delayValue, ok) {
        for (let i = 0; i < netModel.count; ++i) {
            let item = netModel.get(i)
            if (Number(item.port) !== Number(portNumber)) {
                continue
            }
            netModel.setProperty(i, "valueText", ok ? delayValue + "  ms" : qsTr("连接错误"))
            netModel.setProperty(i, "level", ok ? 0 : 3)
            coreModel.coreGlobalError.setStateLevel("网络", i, ok ? 0 : 3)
        }
    }

    function pollNextPort() {
        if (pendingPorts.length === 0) {
            requestRunning = false
            return
        }
        let portNumber = pendingPorts.shift()
        api.__getDelay__(portNumber, function(delayValue) {
            updatePortStatus(portNumber, delayValue, true)
            pollNextPort()
        }, function() {
            updatePortStatus(portNumber, 0, false)
            pollNextPort()
        })
    }

    function refresh() {
        if (requestRunning) {
            return
        }
        let uniquePorts = []
        for (let i = 0; i < netModel.count; ++i) {
            let portNumber = Number(netModel.get(i).port)
            if (isFinite(portNumber) && uniquePorts.indexOf(portNumber) < 0) {
                uniquePorts.push(portNumber)
            }
        }
        if (uniquePorts.length === 0) {
            return
        }
        requestRunning = true
        pendingPorts = uniquePorts
        pollNextPort()
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
            color: Material.color(Material.Blue)
            font.family: "Microsoft YaHei"
            Layout.alignment: Qt.AlignHCenter
        }
        ItemDelegate{
            height: parent.height
            width: height
            ToolTip.visible:hovered
            ToolTip.text: "远程到服务器"
            onClicked:{
                ScriptLauncher.launchScript("/c start /wait mstsc /v "+api.apiConfig.hostname)
            }
            Image {
                width: parent.width
                height: parent.height
                id: image
                source: coreStyle.getIcon("uploading")
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
                    style: coreStyle
                    width: netGrid.cellWidth
                    height:25

                    TapHandler {
                        acceptedButtons: Qt.RightButton
                        onTapped: {
                            root.glob_port = netDelegate.port
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
                api.openApi(glob_port)
            }
        }
        MenuItem{
            text:"重启服务"
            onTriggered:{
            }
        }

    }

}
