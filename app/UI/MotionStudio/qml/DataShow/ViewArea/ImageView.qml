import "../../Controls/TiledImageView"

TiledImageView{
    anchors.fill: parent
    controller: dataAreaShowCore
    apiClient: api
    settings: coreSetting
    surface: surfaceData
    style: coreStyle
    imageUrl: dataAreaShowCore.source
}
