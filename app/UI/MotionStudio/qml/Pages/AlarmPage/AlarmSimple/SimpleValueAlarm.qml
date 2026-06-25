import QtQuick
import QtQuick.Layouts
import QtQuick.Controls
import "../../../Labels"
RowLayout {
    id:root
    property alias title: title_id.text
    property int level: 0
    property var value: ""
    property var displayValue: value
    property real numericValue: numberOr(value, 0)
    height: 30
    width:parent.width
    Layout.fillWidth: true
    readonly property color levelColor:level<=1? Material.color(Material.Green) : level<=2? Material.color(Material.Yellow) : Material.color(Material.Red)
    property string toolTipText: ""

    function numberOr(sourceValue, defaultValue) {
        let numberValue = Number(sourceValue)
        return isFinite(numberValue) ? numberValue : defaultValue
    }
    KeyLabel {
        ItemDelegate{
            width:root.width
            height: root.height
            ToolTip.visible:hovered && root.toolTipText != ""
            ToolTip.text:root.toolTipText
        }
        font.pointSize: 14
        font.bold: true
        font.family: "Microsoft YaHei"
        color:root.levelColor// Material.color(Material.Blue)
        id:title_id
        text: ""
        opacity: 0.9
    }
    ValueTextLabel{
        Layout.fillWidth: true
        id:value_id
        text: root.displayValue
        color:root.levelColor
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
            running: root.level > 2
            color:root.levelColor
        }
    }

    Item{
        width: 10
        height: 1

    }
}
