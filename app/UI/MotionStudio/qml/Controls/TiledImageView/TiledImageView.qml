import QtQuick
import QtQuick.Controls
import QtQuick.Layouts

// TiledImageViewer.qml
Rectangle {
    id: root
    property int tileSize: 8000
    // Tile count per side; fixed to 3x3 for AREA tiles
    property int fixedTileCount: 3
    property int count_ : fixedTileCount
    property string imageUrl: ""
    // viewport is injected from DataShowAreaCore.flick for lazy loading in-view tiles
    property var viewport: dataAreaShowCore ? dataAreaShowCore.flick : null
    property real viewportX: viewport ? viewport.contentX : 0
    property real viewportY: viewport ? viewport.contentY : 0
    property real viewportW: viewport ? viewport.width : width
    property real viewportH: viewport ? viewport.height : height
    property int defaultTileCount: Math.max(1, coreSetting ? coreSetting.defaultAreaTileCount : 3)
    property string previewUrl: dataAreaShowCore && dataAreaShowCore.pre_source ? dataAreaShowCore.pre_source : ""
    // Parallel load toggle; when true all tiles activate immediately
    property bool enableParallelLoad: true
    property int maxParallel: 16
    property int _requestToken: 0
    signal imageInfoReady(string url)
    color: "#00000000"
    property int source_item_width: parseInt(dataAreaShowCore.sourceWidth/count_)
    property int source_item_height: parseInt(dataAreaShowCore.sourceHeight/count_)

    function get_num(px_width){
        let i = 1
        while (true){
            if (px_width / i <= tileSize){
                return i
            }
            i++
        }
    }

    function requestImageInfo() {
        if (!imageUrl || imageUrl.length === 0) {
            return
        }
        const tileRefSize = tileSize * fixedTileCount
        if (dataAreaShowCore && tileRefSize > 0) {
            dataAreaShowCore.sourceWidth = tileRefSize
            dataAreaShowCore.sourceHeight = tileRefSize
        }
        _requestToken += 1
        const currentToken = _requestToken
        api.ajax.get(imageUrl,(text)=>{
                         if (currentToken !== _requestToken){
                             return
                         }
                         let json_data = JSON.parse(text)
                         if (!tileRefSize || tileRefSize <= 0) {
                             dataAreaShowCore.sourceWidth = json_data["width"]
                             dataAreaShowCore.sourceHeight = json_data["height"]
                         }
                         if (count_ !== fixedTileCount) {
                             count_ = fixedTileCount
                         }
                         imageInfoReady(imageUrl)
                     },(err)=>{
                        console.log(err)
                     })
    }

    Component.onCompleted: requestImageInfo()

    onImageUrlChanged: requestImageInfo()

    // Preview background so the area view is not blank while tiles load
    Image {
        anchors.fill: parent
        cache: true
        asynchronous: true
        fillMode: Image.PreserveAspectFit
        source: previewUrl
    }

    Repeater {
        id: tiledImage
        model: count_ * count_
        TiledImageItem{}
    }
}
