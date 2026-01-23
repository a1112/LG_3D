import QtQuick

// TiledImageItem.qml - 多级瓦片叠加加载
// 5个独立的 Image 层（L0-L4）叠加显示，新层加载完成后叠加在旧层上面
Item {
    // 基础属性
    property int row_: 0
    property int col_: 0
    property int count_: 3
    property string imageUrl: ""
    property string previewUrl: ""

    // 视口属性
    property real viewportX: 0
    property real viewportY: 0
    property real viewportW: 0
    property real viewportH: 0
    property bool enableParallelLoad: true

    // ========== 多级加载属性 ==========
    property real currentScale: 1.0
    property int currentLevel: 0
    property int loadedLevel: -1  // 当前已加载的最高级别
    property int targetLevel: 0   // 目标级别（根据缩放计算）

    // ========== 渐进升级配置 ==========
    property bool enableProgressiveUpgrade: true
    property int quickLoadLevel: 0

    // ========== 视口检测 ==========
    readonly property bool isInViewport: {
        const vpX1 = -viewportX
        const vpY1 = -viewportY
        const vpX2 = vpX1 + viewportW
        const vpY2 = vpY1 + viewportH
        const tileX1 = x
        const tileY1 = y
        const tileX2 = tileX1 + width
        const tileY2 = tileY1 + height
        return !(tileX2 <= vpX1 || tileX1 >= vpX2 || tileY2 <= vpY1 || tileY1 >= vpY2)
    }

    readonly property bool shouldLoad: {
        if (!isInViewport) return false
        if (enableParallelLoad) return true
        return isInViewport
    }

    // ========== 调试边框 ==========
    Rectangle{
        anchors.fill: parent
        border.width: 1
        color: "#00000000"
        z: 1000
        visible: coreSetting.showTileDebugBorders  // 由设置控制显示

        border.color: {
            if (!isInViewport) return "#33000000"
            if (loadedLevel < 0) return "#FFA500"
            if (loadedLevel >= targetLevel) return "#00FF00"
            return "#FFFF00"
        }

        Text {
            anchors.centerIn: parent
            text: {
                var txt = "[" + row_ + "," + col_ + "]"
                if (loadedLevel >= 0) {
                    txt += "\nL" + loadedLevel + "/" + targetLevel
                }
                return txt
            }
            color: "white"
            font.pixelSize: 10
            font.bold: true
            style: Text.Outline
            styleColor: "black"
            visible: isInViewport && width > 150
        }
    }

    // ========== 预览图背景 ==========
    Image {
        id: previewImage
        anchors.fill: parent
        cache: true
        asynchronous: true
        fillMode: Image.PreserveAspectCrop
        source: previewUrl
        visible: loadedLevel < 0
        z: 0

        property rect sourceRect: {
            if (previewUrl === "" || !dataAreaShowCore || dataAreaShowCore.sourceWidth === 0) {
                return Qt.rect(0, 0, 0, 0)
            }
            var tileW = dataAreaShowCore.sourceWidth / count_
            var tileH = dataAreaShowCore.sourceHeight / count_
            var x = col_ * tileW
            var y = row_ * tileH
            return Qt.rect(
                x / dataAreaShowCore.sourceWidth,
                y / dataAreaShowCore.sourceHeight,
                tileW / dataAreaShowCore.sourceWidth,
                tileH / dataAreaShowCore.sourceHeight
            )
        }
    }

    // ========== 5个叠加的 Image 层（L0-L4）==========
    // 每层独立加载，新层叠加在旧层上面

    // Level 0
    Image {
        id: levelImage0
        anchors.fill: parent
        cache: true
        asynchronous: true
        fillMode: Image.Stretch
        source: levelSource0
        visible: levelSource0 !== "" && loadedLevel >= 0
        opacity: (targetLevel > 0 && loadedLevel > 0) ? 0.3 : 1.0  // 有更高层时变淡
        z: 1

        Behavior on opacity { NumberAnimation { duration: 200 } }

        onStatusChanged: if (status === Image.Ready) onLevelLoaded(0)
    }

    // Level 1
    Image {
        id: levelImage1
        anchors.fill: parent
        cache: true
        asynchronous: true
        fillMode: Image.Stretch
        source: levelSource1
        visible: levelSource1 !== "" && loadedLevel >= 1
        opacity: (targetLevel > 1 && loadedLevel > 1) ? 0.3 : 1.0
        z: 2

        Behavior on opacity { NumberAnimation { duration: 200 } }

        onStatusChanged: if (status === Image.Ready) onLevelLoaded(1)
    }

    // Level 2
    Image {
        id: levelImage2
        anchors.fill: parent
        cache: true
        asynchronous: true
        fillMode: Image.Stretch
        source: levelSource2
        visible: levelSource2 !== "" && loadedLevel >= 2
        opacity: (targetLevel > 2 && loadedLevel > 2) ? 0.3 : 1.0
        z: 3

        Behavior on opacity { NumberAnimation { duration: 200 } }

        onStatusChanged: if (status === Image.Ready) onLevelLoaded(2)
    }

    // Level 3
    Image {
        id: levelImage3
        anchors.fill: parent
        cache: true
        asynchronous: true
        fillMode: Image.Stretch
        source: levelSource3
        visible: levelSource3 !== "" && loadedLevel >= 3
        opacity: (targetLevel > 3 && loadedLevel > 3) ? 0.3 : 1.0
        z: 4

        Behavior on opacity { NumberAnimation { duration: 200 } }

        onStatusChanged: if (status === Image.Ready) onLevelLoaded(3)
    }

    // Level 4 (最高质量)
    Image {
        id: levelImage4
        anchors.fill: parent
        cache: true
        asynchronous: true
        fillMode: Image.Stretch
        source: levelSource4
        visible: levelSource4 !== "" && loadedLevel >= 4
        opacity: 1.0
        z: 5

        onStatusChanged: if (status === Image.Ready) onLevelLoaded(4)
    }

    // ========== 图像源属性 ==========
    property url levelSource0: ""
    property url levelSource1: ""
    property url levelSource2: ""
    property url levelSource3: ""
    property url levelSource4: ""

    // ========== 构建图像URL ==========
    function buildImageUrl(level) {
        if (imageUrl === "" || imageUrl === undefined) {
            return ""
        }
        var url = imageUrl
        url += "?row=" + row_
        url += "&col=" + col_
        url += "&count=" + count_
        url += "&level=" + level
        return url
    }

    // ========== 级别加载完成回调 ==========
    function onLevelLoaded(level) {
        if (level > loadedLevel) {
            console.log("[Tile " + row_ + "," + col_ + "] L" + level + " loaded, updating loadedLevel: " + loadedLevel + " -> " + level)
            loadedLevel = level

            // 继续加载下一级
            if (enableProgressiveUpgrade && loadedLevel < targetLevel) {
                loadNextLevel.start()
            }
        }
    }

    // ========== 渐进升级定时器 ==========
    Timer {
        id: loadNextLevel
        interval: 100  // 100ms 后加载下一级
        repeat: false
        onTriggered: {
            if (loadedLevel < targetLevel) {
                var nextLevel = loadedLevel + 1
                console.log("[Tile " + row_ + "," + col_ + "] Loading L" + nextLevel + " (target=L" + targetLevel + ")")
                setLevelSource(nextLevel, buildImageUrl(nextLevel))
            }
        }
    }

    // ========== 设置指定级别的图像源 ==========
    function setLevelSource(level, url) {
        if (level === 0) levelSource0 = url
        else if (level === 1) levelSource1 = url
        else if (level === 2) levelSource2 = url
        else if (level === 3) levelSource3 = url
        else if (level === 4) levelSource4 = url
    }

    // ========== 清空所有级别 ==========
    function clearAllLevels() {
        levelSource0 = ""
        levelSource1 = ""
        levelSource2 = ""
        levelSource3 = ""
        levelSource4 = ""
        loadedLevel = -1
        loadNextLevel.stop()
    }

    // ========== 更新等级 ==========
    function updateLevel(newLevel) {
        var oldTargetLevel = targetLevel
        targetLevel = Math.max(0, Math.min(4, newLevel))  // 限制在 0-4 范围内

        // URL 改变，重新加载
        var urlChanged = false
        if (lastLoadedUrl !== imageUrl) {
            urlChanged = true
            lastLoadedUrl = imageUrl
            clearAllLevels()
        }

        // 目标级别改变
        if (oldTargetLevel !== targetLevel) {
            // console.log("[Tile " + row_ + "," + col_ + "] targetLevel: L" + oldTargetLevel + " -> L" + targetLevel)
        }

        // 还没有加载任何瓦片
        if (loadedLevel < 0) {
            var startLevel = enableProgressiveUpgrade ? quickLoadLevel : targetLevel
            console.log("[Tile " + row_ + "," + col_ + "] Quick load L" + startLevel + " (target=L" + targetLevel + ")")
            setLevelSource(startLevel, buildImageUrl(startLevel))
            loadedLevel = startLevel

            // 如果需要升级，启动预加载
            if (enableProgressiveUpgrade && loadedLevel < targetLevel) {
                loadNextLevel.start()
            }
        } else if (loadedLevel < targetLevel) {
            // 需要升级，启动预加载
            if (!loadNextLevel.running) {
                loadNextLevel.start()
            }
        } else if (loadedLevel > targetLevel) {
            // 降级 - 隐藏高于目标级别的层
            // 不需要清空，只是隐藏而已
        }
    }

    // ========== 记录上次加载的 URL ==========
    property string lastLoadedUrl: ""

    // ========== 监听视口变化 ==========
    onIsInViewportChanged: {
        if (isInViewport && loadedLevel < 0) {
            updateLevel(currentLevel)
        }
    }

    // ========== 组件完成时初始加载 ==========
    Component.onCompleted: {
        lastLoadedUrl = imageUrl
        if (shouldLoad) {
            updateLevel(currentLevel)
        }
    }

    // ========== 监听全局等级变化 ==========
    onCurrentLevelChanged: {
        if (isInViewport) {
            updateLevel(currentLevel)
        }
    }

    // ========== 监听 imageUrl 变化 ==========
    onImageUrlChanged: {
        if (isInViewport) {
            updateLevel(currentLevel)
        }
    }

    // ========== 监听 previewUrl 变化 ==========
    onPreviewUrlChanged: {
        if (previewUrl !== "") {
            clearAllLevels()
        }
    }
}
