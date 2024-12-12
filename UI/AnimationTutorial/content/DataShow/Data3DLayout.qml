import QtQuick
import QtQuick.Layouts
import "View3D"
Loader{
    active: surfaceData.is3DrootView
    Layout.fillWidth: true
    Layout.fillHeight:true
    sourceComponent: View3DRoot{
    }
}
