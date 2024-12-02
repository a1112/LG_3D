import QtQuick
import QtQuick.Controls
import "Core"
import "../Core"
import "../GlobalView"
Item{
    id:root
    property SurfaceData surfaceData
    property DataShowCore dataShowCore
    visible: dataShowCore.show_visible
    SplitView.fillHeight: true
    SplitView.fillWidth: true

    Data2DLayout{}

    GlobItemErrorView{

    }
}
