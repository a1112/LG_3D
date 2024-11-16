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

    property ReDetectionStatus reDetectionStatus: ReDetectionStatus{}
    dim:true

    x:parent.width
    id:root
    width: 590
    height: col.height+60

    onOpened:{
        let mmList = coreModel.getCurrentCoilListModelMinMaxId()
        from_id.value=mmList[0]
        to_id.value=mmList[1]
        ws_id.active=true
    }
    ColumnLayout{
        id:col
        width:parent.width
        spacing:20
        Row{
            spacing:20
            Layout.alignment: Qt.AlignHCenter
            Label{
                text: "重新识别"
                font.pixelSize: 25
                font.family:"Microsoft YaHei"
                font.bold: true
                color: Material.color(Material.Brown)
            }
            Button{
                text: "重新连接"
                visible:root.reDetectionStatus.isError
                enabled:root.reDetectionStatus.isError
                onClicked:{
                    ws_id.active=false
                    ws_id.active=true
                }
            }
        }

        RowLayout{
            enabled: root.reDetectionStatus.canChange
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
    }
    RowLayout{

        spacing:10
        Layout.fillWidth: true
        Item{
            enabled: !root.reDetectionStatus.isError
            Layout.fillWidth: true
            implicitHeight:35
            RowLayout{
                anchors.fill: parent
                visible:root.reDetectionStatus.isRuuing || root.reDetectionStatus.isFinished
                ProgressBar{
                    from:0
                    to:1
                    value:root.reDetectionStatus.progress
                    Layout.fillWidth: true
                    id:progressBar
                    indeterminate:root.reDetectionStatus.isRuuing
                }
                KeyLabel{
                    text:root.reDetectionStatus.isRuuing?"运行...":
                                                          root.reDetectionStatus.isFinished?"运行完成":
                                                                                             root.reDetectionStatus.errorStr?"运行失败":
                                                                                                                              root.reDetectionStatus.errorStr
                }
            }
            ErrorLabel{
                anchors.centerIn: parent
                text:root.reDetectionStatus.errorStr
                visible:root.reDetectionStatus.isError
            }

        }
        CheckRecButton{
            Layout.alignment: Qt.AlignVCenter
            text: "识别"
            // enabled: root.reDetectionStatus.canChange
            visible: !root.reDetectionStatus.isError
            onClicked:{
                ws_id.sendTextMessage(
                            JSON.stringify({"from_id":from_id.value,"to_id":to_id.value,"folder":root.outputUrl})
                            )
                root.reDetectionStatus.strat()
            }
        }
    }

    WebSocket{
        id:ws_id
        url:api.getWsReDetectionUrl()
        onTextMessageReceived:(message)=>{
                                  root.reDetectionStatus.setRunning()
                              }
        onErrorStringChanged:(error)=>{
                                 if (error) {
                                     root.reDetectionStatus.setError(error)
                                 }
                                 else{
                                     root.reDetectionStatus.setNone()
                                 }

                             }

        onStatusChanged: {
            if (status === WebSocket.Open) {
                root.reDetectionStatus.setNone()
                root.connected = true

            } else if (status === WebSocket.Closed) {
                root.reDetectionStatus.setError("连接断开!")
                root.connected = false
            }
        }
    }

}

