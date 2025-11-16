import QtQuick 2.15
import QtQuick.Controls 2.15
ItemDelegate {
    property string tipText: ""
    ToolTip.visible: tipText!=="" && hovered
    ToolTip.text: tipText
}
