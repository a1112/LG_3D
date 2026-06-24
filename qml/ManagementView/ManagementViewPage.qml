import QtQuick
import QtQuick.Controls.Material
import QtQuick.Layouts
import SoftMonitor 1.0
import QtQuick.Dialogs
/*
    后台监控
*/
Item {
    id:root
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

    function stopExe(exe){
        return monitor.stopExe(exe)
    }

    function startExe(name){
        return monitor.startExe(name)
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

    DropArea{
        anchors.fill: parent
        onDropped: {
            dialogPop.initExe(drop.urls[0])
        }
    }
}
