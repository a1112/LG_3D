import QtQuick 2.15
import QtQuick.Controls
import QtQuick.Controls.Material
import QtQuick.Layouts
Item {
    id:root
    property string global_key: ""
    property int alarmLevel: 0
    property ListModel cameraModel: ListModel{
    }
    Timer{
        interval: 10000
        running: root.visible
        repeat: true
        triggeredOnStart: true
        onTriggered: {
            api.getCameraAlarm(
                        (result)=>{
                            console.log(result)
                            cameraModel.clear()
                            let data = JSON.parse(result)
                            for(let key in data){
                                data[key]["Key"]=key
                                cameraModel.append(data[key])
                            }
                        },
                        (error)=>{
                            // console.log(error)
                        }
                        )
        }

    }


    ColumnLayout{
        anchors.fill: parent
        Label{
            text:"相机状态"
            font.pointSize: 18
            font.bold: true
            color: Material.color(Material.Blue)
            font.family: "Microsoft YaHei"
            Layout.alignment: Qt.AlignHCenter

        }
        Item{
            id:body
            Layout.fillWidth: true
            Layout.fillHeight: true
            GridView{
                anchors.fill: parent
                model: cameraModel
                cellWidth: parent.width / 3-1
                cellHeight: parent.height/2
                delegate: AlarmItemCamerasItem {
                    width: body.width / 3-1
                    height:body.height/2
                    onClicked:{
                    }

                    MouseArea{
                        anchors.fill: parent
                        acceptedButtons: Qt.RightButton
                        onClicked:{
                            global_key=Key
                            cameraIdMenu.popup()
                        }
                    }
                }
            }


        }
    }

    Menu{
        id:cameraIdMenu
        MenuItem{
            text:"打开当前卷相机数据"
            onTriggered:{
                Qt.openUrlExternally(api.getCameraDataUrl(core.coilIndex,global_key))
            }
        }
        MenuItem{
            text:"打开原始数据保存路径"
            onTriggered:{
            }
        }
        MenuItem{
            text:"重启相机"
            onTriggered:{
            }
        }
    }

}
