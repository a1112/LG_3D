import QtQuick
import QtQuick.Controls
import QtQuick.Controls.Material
import QtQuick.Layouts
import "../../../Base"
import "../../../btns"
Item{
    Frame{
        anchors.fill: parent
    }
    width:root.width/3*2
    height:30
    property string title:"塔形"
    property string value:"100mm"
    RowLayout{
        anchors.fill: parent
        LabelBase{
            opacity:0.7
            text:title+":"
            anchors.verticalCenter: parent.verticalCenter
        }
        LabelBase{
            Layout.fillWidth: true
            text:value
            font.pixelSize: 15
            font.bold:true
        }
    }

}
