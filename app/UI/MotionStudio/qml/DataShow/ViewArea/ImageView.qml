import "../../Controls/TiledImageView"

TiledImageView{
    anchors.fill: parent
    controller: dataAreaShowCore
    apiClient: api
    settings: coreSetting
    surface: surfaceData
    imageUrl: dataAreaShowCore.source
}
