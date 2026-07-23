import QtQuick
import QtQuick.Controls
import QtQuick.Controls.Material
import QtQuick.Layouts
import SoftMonitor 1.0
import QtQuick.Dialogs
/*
    后台监控
*/
Item {
    id:root
    property var currentIssues: []
    property string lastIssueSignature: ""
    property int issueCount: currentIssues.length
    property SoftMonitor monitor:  SoftMonitor{
    }

    property var stateDict: {
        return { "-2":{
                color:"yellow",
                text:"未知"
            },
            "-1":{
                color:"red",
                text:"不存在"
            },
            "0":{
                color:"pink",
                text:"未运行"
            },
            "1":{
                color:"green",
                text:"运行中"
            }
        }

    }
    function getState_(name){
        return monitor.getState_(name)
    }

    function getHeartbeatText(name){
        return monitor.getHeartbeatText(name)
    }

    function stopExe(exe){
        return monitor.stopExe(exe)
    }

    function startExe(name){
        return monitor.startExe(name)
    }

    function restartExe(name){
        return monitor.restartExe(name)
    }

    function changeValue(index,key,value){
        return monitor.changeValue(index,key,value)
    }
    function removeItem(index){
        appModel.remove(index)
        monitor.remove(index)
    }

    function startAll(){
        return monitor.startAll()
    }
    function restartAll(){
        return monitor.restartAll()
    }
    function stopAll(){
        return monitor.closeAll()
    }

    function openIssueDialog(){
        if (currentIssues.length > 0) {
            deviceIssueDialog.open()
        }
    }

    function closeAll(){
        //全部关闭
        return monitor.closeAll()
    }

    function initMonitor(){
        appModel.clear()
        let jsData = monitor.getMonitor()
        jsData = JSON.parse(jsData)
        for (let i = 0; i < jsData.length; i++) {
            jsData[i]["delay"]=parseInt(jsData[i]["delay"])
            appModel.append(jsData[i])
        }
    }

    Component.onCompleted: {
        initMonitor()
    }

    Timer {
        interval: 3000
        running: true
        repeat: true
        triggeredOnStart: true
        onTriggered: {
            let issues = []
            try {
                issues = JSON.parse(monitor.getIssues())
            } catch (error) {
                console.warn("设备问题解析失败", error)
            }
            root.currentIssues = issues
            let keys = []
            for (let i = 0; i < issues.length; ++i) {
                keys.push(issues[i].name + ":" + issues[i].state)
            }
            let signature = keys.join("|")
            if (!signature) {
                root.lastIssueSignature = ""
            } else if (signature !== root.lastIssueSignature
                       && !deviceIssueDialog.visible) {
                root.lastIssueSignature = signature
                deviceIssueDialog.open()
            }
        }
    }
    ListModel{
        id: appModel
    }

    FileDialog{
        id:fileDialog
        nameFilters: ["*.exe"]
        onAccepted: {
         dialogPop.initExe(selectedFile)
        }
    }

    Menu{
        id:base_menu
        MenuItem{
            text:"添加"
            onTriggered: {
                fileDialog.open()
            }
        }
        MenuItem{
            text:"全部启动"
            onTriggered: {
                startAll()
            }
        }
        MenuItem{
            text:"全部关闭"
            onTriggered: {
                stopAll()
            }
        }
        MenuItem{
            text:"全部重启"
            onTriggered: {
                restartAll()
            }
        }
        Menu{
            title:"监听"
        MenuItem{
            text:"全部取消监听"
            onTriggered: {
                for(let i=0;i<appModel.count;i++){
                    appModel.setProperty(i,"monitorAble",false)
                }
            }
        }
        MenuItem{
            text:"全部监听"
            onTriggered: {
                for(let i=0;i<appModel.count;i++){
                    appModel.setProperty(i,"monitorAble",true)
                }
            }
        }
        }

        Menu{
            title:"配置"
        MenuItem{
            text:"打开文件位置"
            onTriggered: {
                let path = monitor.getConfigDirPath()
                Qt.openUrlExternally("file:///"+path)
            }
        }
        MenuItem{
            text:"打开文件"
            onTriggered: {
                let path = monitor.getConfigPath()
                Qt.openUrlExternally("file:///"+path)
            }
        }
        }
    }

    MouseArea{
        anchors.fill: parent
        acceptedButtons: Qt.RightButton
        onClicked: {
            base_menu.popup()
        }
    }

    ColumnLayout{
        anchors.fill: parent
        ListView{
            clip: true
            model: appModel
            Layout.fillWidth: true
            Layout.fillHeight: true
            delegate: ManagementViewItem{
                z:999
                width:root.width
            }
        }
        FootItem{
            height: 30
            Layout.fillWidth: true
        }
    }

    AddPopup{
        id:dialogPop
    }

    Dialog {
        id: deviceIssueDialog
        anchors.centerIn: parent
        width: Math.min(root.width - 40, 620)
        modal: true
        focus: true
        title: qsTr("设备/服务异常")
        closePolicy: Popup.CloseOnEscape

        contentItem: ColumnLayout {
            spacing: 12

            Label {
                Layout.fillWidth: true
                text: qsTr("检测到 %1 个设备服务问题，请检查或执行重启。").arg(root.issueCount)
                wrapMode: Text.WordWrap
                font.bold: true
                color: Material.color(Material.Orange)
            }

            Rectangle {
                Layout.fillWidth: true
                Layout.preferredHeight: Math.min(issueColumn.implicitHeight + 16, 320)
                color: Qt.rgba(1, 1, 1, 0.05)
                radius: 4
                clip: true

                Column {
                    id: issueColumn
                    anchors.fill: parent
                    anchors.margins: 8
                    spacing: 8

                    Repeater {
                        model: root.currentIssues

                        delegate: RowLayout {
                            width: issueColumn.width
                            spacing: 10

                            Label {
                                text: modelData.state === -1 ? "●" : "●"
                                color: modelData.state === -1
                                       ? Material.color(Material.Red)
                                       : Material.color(Material.Orange)
                            }
                            ColumnLayout {
                                Layout.fillWidth: true
                                spacing: 2
                                Label {
                                    Layout.fillWidth: true
                                    text: modelData.name
                                    font.bold: true
                                    elide: Text.ElideRight
                                }
                                Label {
                                    Layout.fillWidth: true
                                    text: modelData.message
                                    opacity: 0.72
                                    elide: Text.ElideRight
                                }
                            }
                            Button {
                                text: qsTr("重启")
                                enabled: modelData.state !== -1
                                onClicked: restartExe(modelData.name)
                            }
                        }
                    }
                }
            }

            RowLayout {
                Layout.fillWidth: true
                Item { Layout.fillWidth: true }
                Button {
                    text: qsTr("重启异常服务")
                    Material.background: Material.Teal
                    onClicked: {
                        for (let i = 0; i < root.currentIssues.length; ++i) {
                            if (root.currentIssues[i].state !== -1) {
                                restartExe(root.currentIssues[i].name)
                            }
                        }
                        deviceIssueDialog.close()
                    }
                }
                Button {
                    text: qsTr("关闭")
                    onClicked: deviceIssueDialog.close()
                }
            }
        }
    }

    DropArea{
        anchors.fill: parent
        onDropped: {
            dialogPop.initExe(drop.urls[0])
        }
    }
}
