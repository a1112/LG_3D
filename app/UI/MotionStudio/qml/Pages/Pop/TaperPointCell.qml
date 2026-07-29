import QtQuick
import QtQuick.Controls

Column {
    id: root

    required property var style
    required property var data
    required property string xKey
    required property string yKey
    required property string valueKey
    property bool emphasizePositive: false

    padding: 2
    spacing: 0

    function format(value) {
        let number = Number(value)
        return isFinite(number) ? number.toFixed(1) : "-"
    }

    Label {
        width: root.width
        text: "x: " + root.format(root.data[root.xKey])
        color: root.style.secondaryTextColor
        font.pixelSize: 9
        horizontalAlignment: Text.AlignHCenter
    }

    Label {
        width: root.width
        text: "y: " + root.format(root.data[root.yKey])
        color: root.style.secondaryTextColor
        font.pixelSize: 9
        horizontalAlignment: Text.AlignHCenter
    }

    Label {
        width: root.width
        text: root.format(root.data[root.valueKey])
        font.pixelSize: 9
        font.bold: root.emphasizePositive
        color: root.emphasizePositive && Number(root.data[root.valueKey]) > 0
               ? root.style.statusErrorColor : root.style.statusSuccessColor
        horizontalAlignment: Text.AlignHCenter
    }
}
