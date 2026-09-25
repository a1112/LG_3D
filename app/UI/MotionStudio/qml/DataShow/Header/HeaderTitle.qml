import QtQuick
import QtQuick.Controls
Row {
    id: root
    required property var surfaceData
    Label{
        font.bold: true
        text: root.surfaceData.key_string + "   "
        font.pointSize: 18
        color: root.surfaceData.keyColor
    }
    Label{
        font.bold: true
        text: root.surfaceData.is2DrootView ? root.surfaceData.currentViewKey
              : root.surfaceData.isAreaRootView ? qsTr("2D相机") : qsTr("3D")
    }
}
