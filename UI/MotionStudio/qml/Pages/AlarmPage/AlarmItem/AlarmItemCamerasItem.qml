import QtQuick 2.15
import QtQuick.Controls
import QtQuick.Controls.Material
import QtQuick.Layouts
ItemDelegate {
    id:root
    property string titleText: Key
    property string valueText: DeviceTemperature+" ℃"
    property string valueColor: coreStyle.labelColor
    ToolTip.visible: hovered
    ToolTip.text: msg
    Frame{
        anchors.fill: parent
    }
RowLayout{
 anchors.fill: parent
    Label{
        text:root.titleText
    }
    Label{
        text: ":"
    }
    Label{
        color: root.valueColor
        font.bold:true
        font.pixelSize: 18
        text: root.valueText
    }
}

}
