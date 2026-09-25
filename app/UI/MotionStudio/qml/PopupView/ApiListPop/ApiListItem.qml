import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
ItemDelegate {
    id: root
    required property var model
    required property var style
    readonly property string requestUrl: root.model.url || ""

    RowLayout{
        anchors.fill: parent
        spacing: 10
        Label{
            text: root.model.timeString || ""
            color: root.style.statusSuccessColor
        }
        Label{
            text: root.model.type || ""
            color: root.style.secondaryTextColor
        }
        Label{
            Layout.fillWidth: true
            text: root.requestUrl
            elide: Text.ElideMiddle
            color: root.style.textColor
        }
        ToolTip.visible: root.hovered && root.requestUrl.length > 0
        ToolTip.text: root.requestUrl
    }
    onClicked: {
        if (/^https?:\/\//i.test(root.requestUrl)) {
            Qt.openUrlExternally(root.requestUrl)
        }
    }
}
