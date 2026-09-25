pragma ComponentBehavior: Bound

import QtQuick

// TiledImageViewer.qml - 多级瓦片加载
Rectangle {
    id: root

    required property var controller
    required property var apiClient
    required property var settings
    required property var surface
    required property var style

    property int tileSize: 5460              // 单个瓦片的目标尺寸
    property int fixedTileCount: 3           // 3x3 瓦片布局
    property int count_ : fixedTileCount
    property string imageUrl: ""
    // viewport is injected from DataShowAreaCore.flick for lazy loading in-view tiles
    property var viewport: controller ? controller.flick : null
    property real viewportX: viewport ? viewport.contentX : 0
    property real viewportY: viewport ? viewport.contentY : 0
    property real viewportW: viewport ? viewport.width : width
    property real viewportH: viewport ? viewport.height : height
    property int defaultTileCount: Math.max(1, settings ? settings.defaultAreaTileCount : 3)
    property string previewUrl: controller && controller.pre_source ? controller.pre_source : ""
    // Low-resolution levels are small enough to load as a complete 3x3 image.
    // Higher levels continue to use viewport loading to avoid decoding all
    // full-resolution tiles at once.
    property bool enableParallelLoad: false
    readonly property bool loadCompleteGrid: enableParallelLoad || currentLevel <= 1
    property int maxParallel: 16
    property int _requestToken: 0
    property var _imageInfoRequest: null
    property bool debugLog: settings ? settings.showTileDebugBorders : false
    property int tileRefreshGeneration: 0

    function debugLogMessage(message) {
        if (debugLog) {
            console.log(message)
        }
    }

    // ========== 多级加载配置 ==========
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

    // 单个瓦片的实际尺寸（从服务端获取后计算）
    readonly property int actualTileWidth: controller.sourceWidth > 0 ? parseInt(controller.sourceWidth / fixedTileCount) : 0
    readonly property int actualTileHeight: controller.sourceHeight > 0 ? parseInt(controller.sourceHeight / fixedTileCount) : 0

    signal imageInfoReady(string url)
    signal levelChanged(int newLevel)

    color: "#00000000"
    property int source_item_width: parseInt(controller.sourceWidth/count_)
    property int source_item_height: parseInt(controller.sourceHeight/count_)

    // ========== 新增：计算当前需要的瓦片等级 ==========
    function calculateNeededLevel() {
        if (!enableMultiLevel || !controller) {
            debugLogMessage("[TiledView] calculateNeededLevel: controller not available, returning 4")
            return 4  // 不启用多级加载或数据不可用时直接用原图
        }

        // 获取当前缩放值
        var scale = controller.canvasScale || 1.0
        currentScale = scale  // 更新内部属性

        // 单个瓦片的显示尺寸（像素）- 使用画布内容尺寸计算
        var actualTileWidth = controller.sourceWidth / fixedTileCount
        var actualTileHeight = controller.sourceHeight / fixedTileCount
        var tileDisplayW = actualTileWidth * scale
        var tileDisplayH = actualTileHeight * scale
        var displaySize = Math.max(tileDisplayW, tileDisplayH)

        debugLogMessage("[TiledView] calculateNeededLevel: sourceW=" + controller.sourceWidth +
                        ", sourceH=" + controller.sourceHeight +
                        ", scale=" + scale.toFixed(4) +
                        ", displaySize=" + displaySize.toFixed(0))

        // 如果显示尺寸无效（初始化中或数值异常），使用默认值
        if (displaySize <= 0 || isNaN(displaySize)) {
            debugLogMessage("[TiledView] calculateNeededLevel: displaySize invalid, returning 2")
            return 2  // 默认使用中等质量
        }

        // 计算原图相对于显示的倍数
        var ratio = originalTileSize / displaySize

        // 根据倍数选择等级
        var level = 0
        if (ratio >= 16) {
            level = 0  // 1/16 原图 (340x340)
        } else if (ratio >= 8) {
            level = 1  // 1/8 原图 (682x682)
        } else if (ratio >= 4) {
            level = 2  // 1/4 原图 (1364x1364)
        } else if (ratio >= 2) {
            level = 3  // 1/2 原图 (2728x2728)
        } else {
            // 小于2倍，使用原图
            level = 4  // 原图瓦片 (5460x5460)
        }

        debugLogMessage("[TiledView] calculateNeededLevel: ratio=" + ratio.toFixed(2) + ", returning level=" + level)
        return level
    }

    // ========== 新增：评估并更新等级 ==========
    property bool isEvaluating: false

    function evaluateLevel(forceUpdate) {
        if (isEvaluating || !enableMultiLevel) {
            return
        }

        isEvaluating = true
        var newLevel = calculateNeededLevel()

        if (newLevel !== currentLevel || forceUpdate) {
            debugLogMessage("[TiledView] Level change: " + currentLevel + " -> " + newLevel + (forceUpdate ? " (forced)" : ""))
            currentLevel = newLevel
            var scale = controller ? controller.canvasScale : 1.0
            currentScale = scale
            levelChanged(newLevel)
            if (forceUpdate) {
                tileRefreshGeneration += 1
            }
        }

        isEvaluating = false
    }

    // ========== 新增：检查瓦片是否在视口内 ==========
    function isTileInView(tileX, tileY, tileW, tileH) {
        // 视口边界（考虑Flickable的contentX/Y是负值）
        var vpX1 = viewportX
        var vpY1 = viewportY
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

    function get_num(px_width){
        if (!isFinite(px_width) || px_width <= 0 || tileSize <= 0) {
            return 1
        }
        let i = 1
        while (true){
            if (px_width / i <= tileSize){
                return i
            }
            i++
        }
    }

    function appendQuery(url, query) {
        if (!url || url.length === 0) {
            return ""
        }
        return url + (url.indexOf("?") >= 0 ? "&" : "?") + query
    }

    function requestImageInfo() {
        _requestToken += 1
        const currentToken = _requestToken
        if (_imageInfoRequest) {
            _imageInfoRequest.abort()
            _imageInfoRequest = null
        }
        if (!imageUrl || imageUrl.length === 0) {
            return
        }
        // 添加 count=0 参数获取图像尺寸信息
        let infoUrl = appendQuery(imageUrl, "count=0")
        debugLogMessage("[TiledView] requestImageInfo: " + infoUrl)
        _imageInfoRequest = apiClient.ajax.get(infoUrl,(text)=>{
                         _imageInfoRequest = null
                         if (currentToken !== _requestToken){
                             return
                         }
                         debugLogMessage("[TiledView] Image info response: " + text)
                         let json_data
                         try {
                             json_data = JSON.parse(text)
                         } catch (error) {
                             debugLogMessage("[TiledView] Invalid image info: " + error)
                             return
                         }
                         // 使用服务端返回的真实尺寸
                         if (json_data["width"] && json_data["height"]) {
                             controller.sourceWidth = json_data["width"]
                             controller.sourceHeight = json_data["height"]
                             debugLogMessage("[TiledView] Set sourceWidth=" + controller.sourceWidth + ", sourceHeight=" + controller.sourceHeight)

                             // 获取尺寸后重新评估等级并强制更新瓦片
                             evaluateLevel(true)
                         }
                         if (count_ !== fixedTileCount) {
                             count_ = fixedTileCount
                         }
                         imageInfoReady(imageUrl)
                     },(err)=>{
                        _imageInfoRequest = null
                        // 保留错误日志用于调试
                        debugLogMessage("[TiledView] Image info error: " + err)
                     })
    }

    Component.onCompleted: {
        requestImageInfo()
        // 初始化等级计算
        evaluateLevel()
    }

    Component.onDestruction: {
        if (_imageInfoRequest) {
            _imageInfoRequest.abort()
            _imageInfoRequest = null
        }
    }

    onImageUrlChanged: {
        count_ = fixedTileCount
        requestImageInfo()
    }

    Repeater {
        id: tiledImage
        model: root.count_ * root.count_
        TiledImageItem{
            required property int index

            settings: root.settings
            style: root.style
            // 瓦片位置和大小
            x: parseInt(index % root.count_) * width
            y: parseInt(index / root.count_) * height
            width: root.width/root.count_
            height: root.height/root.count_

            // 传递给瓦片项的属性
            imageUrl: root.imageUrl
            previewUrl: root.previewUrl
            row_: parseInt(index/root.count_)
            col_: parseInt(index%root.count_)
            count_: root.count_
            viewportX: root.viewportX
            viewportY: root.viewportY
            viewportW: root.viewportW
            viewportH: root.viewportH
            enableParallelLoad: root.loadCompleteGrid

            // 多级加载相关属性
            currentScale: root.currentScale
            currentLevel: root.currentLevel
            refreshGeneration: root.tileRefreshGeneration

            // 钢卷编号
            coilNo: root.surface && root.surface.currentCoilModel ? root.surface.currentCoilModel.coilNo : ""
        }
    }

    Connections {
        target: root.controller
        enabled: root.enableMultiLevel && root.controller !== null

        function onCanvasScaleChanged() {
            scaleEvaluationTimer.restart()
        }
    }

    // Coalesce wheel events instead of polling for a scale change forever.
    Timer {
        id: scaleEvaluationTimer
        interval: 120
        repeat: false
        onTriggered: root.evaluateLevel()
    }
}
