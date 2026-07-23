import QtQuick
import QtQuick.Controls.Material
import QtQuick.Layouts
import DiskMonitor 1.0
import QtQuick.Dialogs
/*
    后台监控
*/
Item {
    id:root
    property DiskMonitor monitor:  DiskMonitor{
    }

    property var stateDict: {
        return { "-2":{
                color:"yellow",
                text:"未知"
            },
            "-1":{
                color:"red",
                text:"异常"
            },
            "0":{
                color:"pink",
                text:"空间不足"
            },
            "1":{
                color:"green",
                text:"正常"
            }
        }
    }
    property var sortEnum: [
        "time","number","chart"
    ]
    property var sortEnumText: [
        "时间","数字","字符"
    ]

    function getState_(name){
        return monitor.getState_(name)
    }
    function changeValue(mountpoint,key,value){
        return monitor.changeValue(mountpoint,key,value)
    }
    function changeMonitorValue(mountpoint,index,key,value){
        return monitor.changeMonitorValue(mountpoint,index,key,value)
    }
    function initMonitor(){
        appModel.clear()
        let jsData = monitor.get_full_disk_info()
        Object.keys(jsData).forEach((key)=>{
                                        appModel.append(jsData[key])
                                    })
    }

    Component.onCompleted: {
        initMonitor()
    }
    ListModel{
        id: appModel
    }
    FolderDialog{
        id:folderDialog
        onAccepted: {
            dialogPop.initExe(selectedFolder)
        }
    }
    Menu{
        id:base_menu
        MenuItem{
            text:"添加"
            onTriggered: {
                folderDialog.open()
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
