import QtQuick 2.15
import QtQuick.Controls
import QtQuick.Controls.Material
import QtQuick.Layouts
import "../../Base"
import "../../btns"
Item{
    Frame{
        anchors.fill: parent
    }
    width:root.width/2-5
    height:25
    property string title:"卷号"
    property string value:"qwewrqtsad"
    property alias valueColor: value_id.color
    RowLayout{
        anchors.fill: parent
        LabelBase{
            opacity:0.7
            text:title+":"
            Layout.alignment:Qt.AlignVCenter
        }
        LabelBase{
            id:value_id
            Layout.fillWidth: true
            text:value
            font.pixelSize: 17
            font.bold:true
        }
    }

}
