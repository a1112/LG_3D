import QtQuick
import QtQuick.Controls
import QtQuick.Controls.Material
import QtQuick.Layouts
import "../../Base"
import "../../btns"
Item{
    id: root

    Frame{
        anchors.fill: parent
    }
    width: parent ? parent.width / 2 - 5 : 0
    height:25
    property string title:"卷号"
    property string value:"qwewrqtsad"
    property alias valueColor: value_id.color
    RowLayout{
        anchors.fill: parent
        LabelBase{
            opacity:0.7
            text: root.title + ":"
            Layout.alignment:Qt.AlignVCenter
        }
        LabelBase{
            id:value_id
            Layout.fillWidth: true
            text: root.value
            font.pixelSize: 17
            font.bold:true
        }
    }

}
