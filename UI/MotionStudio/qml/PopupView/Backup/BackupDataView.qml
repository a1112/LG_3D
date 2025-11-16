import QtQuick
import QtQuick.Controls
import QtQuick.Controls.Material
import QtQuick.Layouts
import QtWebSockets
import "../../Input"
import "../../Labels"
import "../../Pages/Header"
import QtCore
Menu{

    property BackupStatus backupStatu: BackupStatus{}
    dim:true

    x:parent.width
    id:root
    width: 590
    height: col.height+80

    property string outputFolder:(""+StandardPaths.writableLocation(StandardPaths.DesktopLocation)).substring(8)
    property string outputName:Qt.formatDateTime(new Date(), "备份_yyyy_MM_dd hh_mm_ss")

    property string outputUrl:outputFolder+"/"+outputName

    onOpened:{
        let mmList = coreModel.getCurrentCoilListModelMinMaxId()
        from_id.value=mmList[0]
        to_id.value=mmList[1]
        outputName=Qt.formatDateTime(new Date(), "备份_yyyy_MM_dd hh_mm_ss")
        ws_id.active=true
    }
    ColumnLayout{
        id:col
        width:parent.width
        spacing:20
        Row{
            spacing:10
            Layout.alignment: Qt.AlignHCenter
            Label{
            text: "数据备份"
            font.pixelSize: 25
            font.family:"Microsoft YaHei"
            font.bold: true

            color: Material.color(Material.Orange)
        }
            Button{
            text: "重新连接"
            visible:root.backupStatu.isError
            enabled:root.backupStatu.isError
            onClicked:{
                ws_id.active=false
                ws_id.active=true
            }
            }
        }

        RowLayout{
            enabled: root.backupStatu.canChange
            spacing:10
            Layout.fillWidth: true
            SimpleTextInput{
                id:from_id
                text:"起始流水号"
            }
            SimpleTextInput{
                id:to_id
                text:"结束流水号"
            }
        }
        SimpleFolderInput{
            enabled: root.backupStatu.canChange
            id:folder_id
            text:"保存位置"
            value:outputUrl
            onValueChanged:outputUrl=value
            placeholderText:"桌面/"+ root.outputName
        }
    }
    // onAccepted:{
    //     api.setBackupImageTask(from_id.value,to_id.value,folder_id.value)
    // }
    RowLayout{

        spacing:10
        Layout.fillWidth: true
        Item{
            enabled: !root.backupStatu.isError
            Layout.fillWidth: true
            height:35
            RowLayout{
                anchors.fill: parent
                visible:root.backupStatu.isRuuing || root.backupStatu.isFinished
            ProgressBar{
                from:0
                to:1
                value:root.backupStatu.progress
                Layout.fillWidth: true
                id:progressBar
                indeterminate:root.backupStatu.isRuuing
            }
            KeyLabel{
                text:root.backupStatu.isRuuing?"备份中...":
                    root.backupStatu.isFinished?"备份完成":
                    root.backupStatu.errorStr?"备份失败":
                    root.backupStatu.errorStr
            }
            CheckRecButton{
                text: "打开文件夹"
                onClicked:{
                    Qt.openUrlExternally("file:///"+root.outputUrl)}
            }
            }
            ErrorLabel{
                anchors.centerIn: parent
                text:root.backupStatu.errorStr
                visible:root.backupStatu.isError
            }

        }
        CheckRecButton{
            Layout.alignment: Qt.AlignVCenter
            text: "备份"
            enabled: root.backupStatu.canChange
            visible: !root.backupStatu.isError
            onClicked:{
                root.outputUrl = folder_id.value
                if (!root.outputUrl){
                    root.outputUrl =root.outputFolder+"/"+root.outputName
                }
                ws_id.sendTextMessage(
                            JSON.stringify({"from_id":from_id.value,"to_id":to_id.value,"folder":root.outputUrl})
                            )
                root.backupStatu.strat()
            }
        }

    }



    WebSocket{
        id:ws_id
        url:api.getWsBackupImageUrl()
        onTextMessageReceived:(message)=>{
                                  root.backupStatu.setRunning()
                                  if (parseInt(message)>=100) {
                                    root.backupStatu.setFinished()
                                      root.backupStatu.progress=1.0
                                      Qt.openUrlExternally("file:///"+root.outputUrl)
                                  }
                              }
        onErrorStringChanged:(error)=>{
                             if (error) {
                                 root.backupStatu.setError(error)
                                 }
                                 else{
                                 root.backupStatu.setNone()
                                 }

                             }

        onStatusChanged: {
            if (status === WebSocket.Open) {
                root.backupStatu.setNone()
                root.connected = true
            } else if (status === WebSocket.Closed) {
                root.backupStatu.setError("连接断开!")
                root.connected = false
            }
        }
    }
}

