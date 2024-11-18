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
        text:surfaceData.rootViewIndex==0?surfaceData.currentViewKey: "3D"
    }
}
