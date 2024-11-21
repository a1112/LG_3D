import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import "Core"
import "../Core"
Item{
    id:root

    visible: surfaceData.show_visible

    SplitView.fillHeight: true
    SplitView.fillWidth: true

    property SurfaceData surfaceData
    property DataShowCore dataShowCore: DataShowCore{}
    Data2DLayout{}


}
