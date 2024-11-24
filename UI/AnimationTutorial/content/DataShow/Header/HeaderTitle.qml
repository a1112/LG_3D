import QtQuick
import QtQuick.Controls
Row {
    Label{
        font.bold: true
        text:surfaceData.key+"   "
        font.pointSize: 16
        color: surfaceData.keyColor
    }
    Label{
        font.bold: true
        text:surfaceData.is2DrootView?surfaceData.currentViewKey: "3D"
    }
}
