import QtQuick 2.15
import QtQuick.Controls
import QtQuick.Controls.Material
import QtQuick.Layouts
import "../../../Comp/Card"
CardBase {
    id:root
    property string global_key: ""
    property bool showMore: false
    height: coll.height
    title: "报警综合"
    max_height:160
    content_body:Column{
        id:coll
        Layout.fillWidth: true
        width:parent.width
        // Row{
        //                 x:root.width/2-width/2
        //                 spacing:5
        // Label{
        //     id:showLab
        //     text:"报警综合"
        //     font.pointSize: 18
        //     font.bold: true
        //     color:coreAlarmInfo.alarmColor
        //     font.family: "Microsoft YaHei"
        // }


        // Image{
        //     visible:coreAlarmInfo.hasAlarm
        //     source:"../../../icons/alarm2.png"
        //     width:height
        //     height:showLab.height
        //     fillMode:Image.PreserveAspectFit
        // }
        // }

        AlarmItemSimpleView{
        }

        }

    MouseArea{
        anchors.fill:parent
        acceptedButtons:Qt.RightButton
        onClicked:{
        menu.popup()
        }

    }
    Menu{
        id:menu
        MenuItem{
            text:"查看原始数据"
            onClicked:{
               Qt.openUrlExternally(api.getLastUrlByKey("coilAlarm"))
            }
        }
    }

    }
