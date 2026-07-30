import QtQuick
import QtQuick.Controls
import QtQuick.Controls.Material
import QtQuick.Layouts
import "../../Base"
import "../../btns"
Item {
    id: itemRoot
    Frame{
        anchors.fill: parent
    }
    width: parent ? parent.width / 2 - 1 : 0
    height:30
    property string title:"塔形"
    property string value:"100mm"
    RowLayout{
        anchors.fill: parent
        LabelBase{
            opacity:0.7
            text: itemRoot.title + ":"
            Layout.alignment:Qt.AlignVCenter
        }
        LabelBase{
            Layout.fillWidth: true
            text: itemRoot.value
            font.pixelSize: 15
            font.bold:true
        }
    }

}
