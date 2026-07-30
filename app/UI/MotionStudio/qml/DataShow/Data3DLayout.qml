pragma ComponentBehavior: Bound

import QtQuick
import QtQuick.Layouts
import "View3D"
Loader{
    id: root

    required property var surfaceData
    required property var dataShowCore
    required property var view3DController
    required property var style

    active: root.surfaceData.is3DrootView
    Layout.fillWidth: true
    Layout.fillHeight:true
    asynchronous : true
    sourceComponent: View3DRoot{
        surfaceData: root.surfaceData
        dataShowCore: root.dataShowCore
        view3DController: root.view3DController
        style: root.style
    }
}
