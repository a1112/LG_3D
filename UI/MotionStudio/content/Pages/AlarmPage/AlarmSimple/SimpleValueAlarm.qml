import QtQuick
import QtQuick.Layouts
import QtQuick.Controls
import "../../../Labels"
RowLayout {
    id:root
    property alias title: title_id.text
    property int level: 0
    property real value
    height: 30
    width:parent.width
    Layout.fillWidth: true
    readonly property color levelColor:level<=1? Material.color(Material.Green) : level<=2? Material.color(Material.Yellow) : Material.color(Material.Red)
    property string toolTipText: ""
    KeyLabel {
        ItemDelegate{
            width:root.width
            height: root.height
            ToolTip.visible:hovered && toolTipText != ""
            ToolTip.text:toolTipText
        }
        font.pointSize: 14
        font.bold: true
        font.family: "Microsoft YaHei"
        color:levelColor// Material.color(Material.Blue)
        id:title_id
        text: ""
        opacity: 0.9
    }
    ValueTextLabel{
        Layout.fillWidth: true
        id:value_id
        text: value
        color:levelColor
    }
    KeyLabel {
        text: "mm  "
        opacity: 0.5
        font.bold: true
    }
    Item{
        width:30
        height:width
        SimpleLigth{
            anchors.centerIn: parent
            running: level > 2
            color:levelColor
        }
    }

    Item{
        width: 10
        height: 1

    }
}
