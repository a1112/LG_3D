import QtQuick

// TiledImageItem.qml - 简化版：直接加载目标级别瓦片
Item {
    // 基础属性
    property int row_: 0
    property int col_: 0
    property int count_: 3
    property string imageUrl: ""
    property string previewUrl: ""
    property string coilNo: ""  // 钢卷编号

    // 视口属性
    property real viewportX: 0
    property real viewportY: 0
    property real viewportW: 0
    property real viewportH: 0
    property bool enableParallelLoad: true

    // ========== 多级加载属性 ==========
    property real currentScale: 1.0
    property int currentLevel: 0
    property int loadedLevel: -1
    property int targetLevel: 0

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
        if (!isInViewport) {
            return false
        }
        if (enableParallelLoad) {
            return true
        }
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
                if (coilNo) {
                    txt += "\n" + coilNo
                }
                if (loadedLevel >= 0) {
                    txt += "\nL" + loadedLevel
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

    // ========== 预览图像（灰度，快速加载）==========
    Image {
        id: previewImage
        anchors.fill: parent
        asynchronous: true
        fillMode: Image.Stretch
        source: grayscaleSource
        cache: true
        z: 0
        visible: grayscaleSource !== "" && loadedLevel < 0

        onStatusChanged: function(status) {
            if (status === Image.Ready) {
                // 预览图加载完成后，开始加载目标级别的图像
                updateLevel(currentLevel)
            }
        }
    }

    // ========== 5个叠加的 Image 层（L0-L4）==========
    // Level 0
    Image {
        id: levelImage0
        anchors.fill: parent
        cache: true
        asynchronous: true
        fillMode: Image.Stretch
        source: levelSource0
        visible: levelSource0 !== "" && targetLevel === 0
        z: 1

        onStatusChanged: function(status) {
            if (status === Image.Ready) {
                loadedLevel = 0
            }
        }
    }

    // Level 1
    Image {
        id: levelImage1
        anchors.fill: parent
        cache: true
        asynchronous: true
        fillMode: Image.Stretch
        source: levelSource1
        visible: levelSource1 !== "" && targetLevel === 1
        z: 2

        onStatusChanged: function(status) {
            if (status === Image.Ready) {
                loadedLevel = 1
            }
        }
    }

    // Level 2
    Image {
        id: levelImage2
        anchors.fill: parent
        cache: true
        asynchronous: true
        fillMode: Image.Stretch
        source: levelSource2
        visible: levelSource2 !== "" && targetLevel === 2
        z: 3

        onStatusChanged: function(status) {
            if (status === Image.Ready) {
                loadedLevel = 2
            }
        }
    }

    // Level 3
    Image {
        id: levelImage3
        anchors.fill: parent
        cache: true
        asynchronous: true
        fillMode: Image.Stretch
        source: levelSource3
        visible: levelSource3 !== "" && targetLevel === 3
        z: 4

        onStatusChanged: function(status) {
            if (status === Image.Ready) {
                loadedLevel = 3
            }
        }
    }

    // Level 4 (最高质量)
    Image {
        id: levelImage4
        anchors.fill: parent
        cache: true
        asynchronous: true
        fillMode: Image.Stretch
        source: levelSource4
        visible: levelSource4 !== "" && targetLevel === 4
        z: 5

        onStatusChanged: function(status) {
            if (status === Image.Ready) {
                loadedLevel = 4
            }
        }
    }

    // ========== 图像源属性 ==========
    property url levelSource0: ""
    property url levelSource1: ""
    property url levelSource2: ""
    property url levelSource3: ""
    property url levelSource4: ""

    // 灰度预览图（快速加载）
    property url grayscaleSource: ""

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

    // ========== 加载灰度预览图（快速显示）==========
    function loadGrayscalePreview() {
        if (imageUrl === "" || imageUrl === undefined) {
            return
        }
        // 添加 thumbnail=true 和 grayscale=true
        var url = imageUrl + "?thumbnail=true&grayscale=true"
        grayscaleSource = url
    }

    // ========== 更新等级 ==========
    function updateLevel(newLevel) {
        // 如果imageUrl为空，不进行加载
        if (imageUrl === "" || imageUrl === undefined) {
            return
        }

        var oldTargetLevel = targetLevel
        targetLevel = Math.max(0, Math.min(4, newLevel))

        // URL 改变，重新加载
        var urlChanged = false
        if (lastLoadedUrl !== imageUrl) {
            urlChanged = true
            lastLoadedUrl = imageUrl
            // 清空所有级别
            levelSource0 = ""
            levelSource1 = ""
            levelSource2 = ""
            levelSource3 = ""
            levelSource4 = ""
            loadedLevel = -1
        }

        // 目标级别改变，直接加载目标级别
        if (oldTargetLevel !== targetLevel || urlChanged) {
            // 直接设置目标级别的源
            if (targetLevel === 0) levelSource0 = buildImageUrl(0)
            else if (targetLevel === 1) levelSource1 = buildImageUrl(1)
            else if (targetLevel === 2) levelSource2 = buildImageUrl(2)
            else if (targetLevel === 3) levelSource3 = buildImageUrl(3)
            else levelSource4 = buildImageUrl(4)

            console.log("[Tile " + row_ + "," + col_ + "] CoilNo:" + coilNo + " Loading L" + targetLevel)
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
            // 先加载灰度预览图
            loadGrayscalePreview()
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
        // URL 变化时，重置 lastLoadedUrl 强制检测为变化
        lastLoadedUrl = ""
        // 清空所有级别源，确保重新加载
        levelSource0 = ""
        levelSource1 = ""
        levelSource2 = ""
        levelSource3 = ""
        levelSource4 = ""
        grayscaleSource = ""
        loadedLevel = -1

        if (isInViewport) {
            // 先加载灰度预览图（快速显示）
            loadGrayscalePreview()
            // 然后由 previewImage 的 onStatusChanged 触发目标级别加载
        }
    }

    // ========== 监听 previewUrl 变化 ==========
    onPreviewUrlChanged: {
        // 不再使用预览图，直接加载瓦片
    }
}
