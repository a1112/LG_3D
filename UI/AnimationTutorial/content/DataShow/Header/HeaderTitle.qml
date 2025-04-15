import QtQuick
import QtQuick.Controls
Row {
    Label{
        font.bold: true
        text:surfaceData.key_string+"   "
        font.pointSize: 18
        color: surfaceData.keyColor
    }
    Label{
        font.bold: true
        text:surfaceData.is2DrootView?surfaceData.currentViewKey:
                    surfaceData.isAreaRootView? "2D相机":                   "3D"
    }
}
