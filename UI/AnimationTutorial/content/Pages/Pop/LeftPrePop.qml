import QtQuick
import QtQuick.Controls
import QtQuick.Controls.Material
import QtQuick.Layouts
import "../../Labels"
import "../../Model"
Menu {
    visible: leftCore.isHoved
    id:root
    x: left.width+20
    y:Math.max(20,Math.min(leftCore.hoverPoint.y,leftCore.hoverPoint.y-height-20))
    width:620 //col.width+20
    height:620 //col.height+30
    property int body_width:width-20
    property CoilModel coilModel:leftCore.hovedCoilModel

    onClosed:{
        if (leftCore.isHoved)
            open()
    }
    Item{
        anchors.fill:parent
        Label{    // title
            text:qsTr("数据摘要")
            anchors.left: parent.Left
            color:Material.color(Material.Orange)
        }
        ColumnLayout{
            id:col
            anchors.fill:parent
            spacing:2
            TitleLabel{
                text:coilModel.coilNo
                color:Material.color(Material.Blue)
                anchors.horizontalCenter:parent.horizontalCenter
                font.pointSize: 20
            }
            ImageRow{
            }
            CoilInfo{
                width:  root.width
                height: 100
            }
            AlarmInfo{
                width:body_width
            }
            // TextArea{
            //     text:leftCore.leftMsg
            // }
            DefectInfo{
                Layout.fillWidth:true
                width:body_width
                Layout.fillHeight:true
            }
        }
    }







}
