import "Base"
import "ShowDefects"
// 缺陷信息
DataShowItemBase{
    id: root

    required property var surfaceData
    required property var controller
    required property var areaController
    required property var style
    required property var apiClient
    required property var globalContext

ShowDefectView{
    anchors.fill:parent
    surfaceData: root.surfaceData
    controller: root.controller
    areaController: root.areaController
    style: root.style
    apiClient: root.apiClient
    globalContext: root.globalContext
}

}
