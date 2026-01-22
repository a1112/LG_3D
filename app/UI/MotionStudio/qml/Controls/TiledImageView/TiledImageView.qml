import QtQuick
import QtQuick.Controls
import QtQuick.Layouts

// TiledImageViewer.qml - 多级瓦片加载
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

    // ========== 新增：多级加载配置 ==========
    property int originalTileSize: 5460          // 原图瓦片尺寸（3x3切分后的单个瓦片大小）
    property real scaleThreshold: 1.5            // 1.5倍阈值（超过后使用原图）
    property real currentScale: 1.0              // 当前缩放倍数（通过updateScale函数更新）
    property int currentLevel: 0                 // 当前加载等级 (0-4)
    property bool enableMultiLevel: true         // 启用多级加载

    // 瓦片等级定义
    readonly property var tileLevels: [
        {size: 340, quality: 60},    // Level 0: 1/16 缩略图
        {size: 682, quality: 70},    // Level 1: 1/8
        {size: 1364, quality: 80},   // Level 2: 1/4
        {size: 2728, quality: 90},   // Level 3: 1/2
        {size: 5460, quality: 95}    // Level 4: 原图
    ]

    signal imageInfoReady(string url)
    signal levelChanged(int newLevel)

    color: "#00000000"
    property int source_item_width: parseInt(dataAreaShowCore.sourceWidth/count_)
    property int source_item_height: parseInt(dataAreaShowCore.sourceHeight/count_)

    // ========== 新增：计算当前需要的瓦片等级 ==========
    function calculateNeededLevel() {
        if (!enableMultiLevel || !dataAreaShowCore) {
            return 4  // 不启用多级加载或数据不可用时直接用原图
        }

        // 获取当前缩放值
        var scale = dataAreaShowCore.canvasScale || 1.0
        currentScale = scale  // 更新内部属性

        // 单个瓦片的显示尺寸（像素）
        var tileDisplayW = (root.width / fixedTileCount) * scale
        var tileDisplayH = (root.height / fixedTileCount) * scale
        var displaySize = Math.max(tileDisplayW, tileDisplayH)

        // 计算原图相对于显示的倍数
        var ratio = originalTileSize / displaySize

        // 根据倍数选择等级
        var level = 0
        if (ratio >= 16) {
            level = 0  // 1/16 原图
        } else if (ratio >= 8) {
            level = 1  // 1/8 原图
        } else if (ratio >= 4) {
            level = 2  // 1/4 原图
        } else if (ratio >= 2) {
            level = 3  // 1/2 原图
        } else {
            // 小于2倍或超过1.5倍阈值，使用原图
            level = 4
        }

        return level
    }

    // ========== 新增：评估并更新等级 ==========
    property bool isEvaluating: false

    function evaluateLevel() {
        if (isEvaluating || !enableMultiLevel) {
            return
        }

        isEvaluating = true
        var newLevel = calculateNeededLevel()

        if (newLevel !== currentLevel) {
            var scale = dataAreaShowCore ? dataAreaShowCore.canvasScale : 1.0
            console.log("[TiledView] Scale:" + scale.toFixed(2) + " Level:" + currentLevel + " → " + newLevel)
            currentLevel = newLevel
            currentScale = scale
            levelChanged(newLevel)

            // 通知所有瓦片更新
            updateAllTiles()
        }

        isEvaluating = false
    }

    // ========== 新增：更新所有瓦片 ==========
    function updateAllTiles() {
        for (var i = 0; i < tiledImage.count; i++) {
            var item = tiledImage.itemAt(i)
            if (item && item.updateLevel) {
                item.updateLevel(currentLevel)
            }
        }
    }

    // ========== 新增：检查瓦片是否在视口内 ==========
    function isTileInView(tileX, tileY, tileW, tileH) {
        // 视口边界（考虑Flickable的contentX/Y是负值）
        var vpX1 = -viewportX
        var vpY1 = -viewportY
        var vpX2 = vpX1 + viewportW
        var vpY2 = vpY1 + viewportH

        // 瓦片边界
        var tX1 = tileX
        var tY1 = tileY
        var tX2 = tX1 + tileW
        var tY2 = tY1 + tileH

        // 检查是否相交
        return !(tX2 <= vpX1 || tX1 >= vpX2 || tY2 <= vpY1 || tY1 >= vpY2)
    }

    // ========== 监听视口和尺寸变化 ==========
    onViewportXChanged: evaluateLevel()
    onViewportYChanged: evaluateLevel()
    onWidthChanged: evaluateLevel()
    onHeightChanged: evaluateLevel()

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

    Component.onCompleted: {
        requestImageInfo()
        // 初始化等级计算
        evaluateLevel()
    }

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
        TiledImageItem{
            // 瓦片位置和大小
            x: parseInt(index / count_)*width
            y: parseInt(index%count_)*height
            width: root.width/count_
            height: root.height/count_

            // 传递给瓦片项的属性
            imageUrl: root.imageUrl
            row_: parseInt(index/count_)
            col_: parseInt(index%count_)
            count_: root.count_
            viewportX: root.viewportX
            viewportY: root.viewportY
            viewportW: root.viewportW
            viewportH: root.viewportH
            enableParallelLoad: root.enableParallelLoad

            // 新增：多级加载相关属性
            currentScale: root.currentScale
            currentLevel: root.currentLevel
            inView: root.isTileInView(x, y, width, height)
            tileLevels: root.tileLevels
        }
    }

    // ========== 定期检查缩放变化 ==========
    Timer {
        id: scaleCheckTimer
        interval: 100  // 每100ms检查一次
        repeat: true
        running: enableMultiLevel && dataAreaShowCore !== null

        onTriggered: {
            if (dataAreaShowCore) {
                var newScale = dataAreaShowCore.canvasScale || 1.0
                // 只有缩放变化超过阈值时才重新计算（避免频繁计算）
                if (Math.abs(newScale - currentScale) > 0.05) {
                    evaluateLevel()
                }
            }
        }
    }
}
