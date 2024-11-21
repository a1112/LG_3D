import QtQuick 2.15
import QtQuick.Controls
import QtQuick.Controls.Material
import QtQuick.Layouts
import "../../Base"
import "../../Comp/Card"
import "../../btns"
CardBase {
    id:root
    Layout.fillWidth: true
    max_height:165//col.height+10
    title:  core.currentCoilModel.coilNo        //"当前卷信息"
    // content_head_tool:ColorImageButton{
    //     source: "../icons/defectInfo.png"
    //     width: 30
    //     selectColor: Material.color(Material.LightGreen)
    //     height: 30
    //     ItemDelegate{
    //         anchors.fill: parent
    //         onClicked: {
    //             app.showDefectInfo()
    //         }
    //     }
    // }

    content_body:Item{
        id:col
        width:root.width
        Layout.fillWidth: true
        Layout.fillHeight: true
                visible: root.isShow
        Flow{
            anchors.fill: parent
            Layout.fillWidth: true
            Layout.fillHeight: true
            FlowRowItem{
                title:"流水号"
                value:core.currentCoilModel["coilId"]
                valueColor:Material.color(Material.Green)
            }
            FlowRowItem{
                title:"去向"
                value:core.currentCoilModel.nextInfo
            }
            FlowRowItem{
                title:"卷号 "
                value:core.currentCoilModel.coilNo
            }
            FlowRowItem{
                title:"钢种 "
                value:core.currentCoilModel.coilType
            }
            FlowRowItem{
                title:"外径 "
                value:core.currentCoilModel.coilDia
            }
            FlowRowItem{
                title:"内径 "
                value:core.currentCoilModel.coilInside
            }
            FlowRowItem{
                title:"卷宽 "
                value:core.currentCoilModel.coilWidth
            }
            FlowRowItem{
                title:"卷厚 "
                value:core.currentCoilModel.coilThickness
            }
            FlowRowItem{
                title:"日期 "
                value:core.currentCoilModel.coilDetectionTime.dataString
            }
            FlowRowItem{
                title:"时间 "
                value:core.currentCoilModel.coilDetectionTime.timeString
            }
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
            text:"更多信息..."
            onClicked:{
               app.showDefectInfo()
            }
        }
    }
}
