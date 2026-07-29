import QtQuick
import QtQuick.Controls
import "Core"
import "../Core/Surface"
import "../GlobalView"
import "View3D"
Item{
    id:root
    required property SurfaceData surfaceData
    required property DataShowCore dataShowCore
    required property var modelStore
    required property var style
    required property var settings
    required property var adaptiveMetrics
    required property var alarmInfo
    required property var apiClient
    property var dataShowCore_: surfaceData.isAreaRootView ? dataShowCore.dataShowAreaCore:dataShowCore

    readonly property DataShowControl controls:dataShowCore.controls

    visible: true//dataShowCore.show_visible
    SplitView.fillHeight: true
    SplitView.fillWidth: true

    property Core3D core3D: Core3D{}

    DataLayout{
        surfaceData: root.surfaceData
        modelStore: root.modelStore
        controller: root.dataShowCore
        areaController: root.dataShowCore_
        style: root.style
        settings: root.settings
        adaptiveMetrics: root.adaptiveMetrics
        alarmInfo: root.alarmInfo
        apiClient: root.apiClient
    }

    GlobItemErrorView{}

}
