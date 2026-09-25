import QtQuick
import QtQuick.Controls

Row {
    id: root
    required property var surfaceData
    required property var style

    Label{
        text: "" + parseInt(root.surfaceData.medianZInt)
        color: root.style.statusWarningColor
        font.bold: true
    }
    Label{
        text: "  " + parseInt(root.surfaceData.medianZ)
        color: root.style.statusSuccessColor
        font.bold: true
    }

}
