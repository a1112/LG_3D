import QtQuick
import QtQuick.Controls
import "Core"
import "../Core/Surface"
import "../GlobalView"
import "View3D"
Item{
    id:root
    property SurfaceData surfaceData
    property DataShowCore dataShowCore
    property var dataShowCore_: surfaceData.isAreaRootView ? dataShowCore.dataShowAreaCore:dataShowCore

    readonly property DataShowControl controls:dataShowCore.controls

    visible: true//dataShowCore.show_visible
    SplitView.fillHeight: true
    SplitView.fillWidth: true

    property Core3D core3D: Core3D{}

    DataLayout{}

    GlobItemErrorView{}

}
