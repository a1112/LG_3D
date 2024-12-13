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

    readonly property DataShowControl controls:dataShowCore.controls

    visible: dataShowCore.show_visible
    SplitView.fillHeight: true
    SplitView.fillWidth: true

    property Core3D core3D: Core3D{}

    DataLayout{}

    GlobItemErrorView{

    }
}
