import QtQuick
import QtQuick.Controls
import "Core"
import "../Core"
import "../GlobalView"
import "View3D"
Item{
    id:root
    property SurfaceData surfaceData
    property DataShowCore dataShowCore
    visible: dataShowCore.show_visible
    SplitView.fillHeight: true
    SplitView.fillWidth: true

    property Core3D core3D: Core3D{}

    DataLayout{}

    GlobItemErrorView{

    }
}
