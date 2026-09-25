import "../../Controls/TiledImageView"

TiledImageView {
    id: root
    required property var areaController
    required property var apiService
    required property var settingsStore
    required property var surfaceData
    required property var appStyle

    anchors.fill: parent
    controller: root.areaController
    apiClient: root.apiService
    settings: root.settingsStore
    surface: root.surfaceData
    style: root.appStyle
    imageUrl: root.areaController.source
}
