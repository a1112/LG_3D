import QtQuick 2.15
import QtQuick.Controls
import QtQuick.Layouts
ItemDelegate {
    id:root
    required property string key
    required property string value
    required property string msg
    required property int level
    required property var style

    readonly property string titleText: key
    readonly property string valueText: value
    readonly property color valueColor: level >= 3
                                        ? style.statusErrorColor
                                        : level >= 2
                                          ? style.statusWarningColor
                                          : style.statusSuccessColor
    ToolTip.text: msg
    ToolTip.visible:hovered
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
