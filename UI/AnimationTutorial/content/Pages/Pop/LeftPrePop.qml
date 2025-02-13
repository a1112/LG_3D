import QtQuick
import QtQuick.Controls
import QtQuick.Controls.Material
import QtQuick.Layouts
import "../../Labels"
import "../../Model"
Popup {
    id:root
    width:620 //col.width+20
    property int body_width:width-20
    height: col.height+30
    visible: leftCore.isHoved

    property CoilModel coilModel:leftCore.hovedCoilModel

    onClosed:{
        if (leftCore.isHoved)
            open()
    }

    x: left.width+20
    y:Math.max(20,Math.min(leftCore.hoverPoint.y,leftCore.hoverPoint.y-height-20))

    Label{    // title
        text:qsTr("数据摘要")
        anchors.left: parent.Left
        color:Material.color(Material.Orange)

    }

    Column{
        id:col
        spacing:10
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
        DefectInfo{
            width:body_width
        }
        TextArea{
            text:leftCore.leftMsg
        }
    }

}
