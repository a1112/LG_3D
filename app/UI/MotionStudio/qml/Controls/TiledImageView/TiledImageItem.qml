import QtQuick

// TiledImageItem.qml - 多级瓦片加载
Item{
    // 基础属性
    property int row_: 0
    property int col_: 0
    property int count_: 3
    property string imageUrl: ""

    // 视口属性
    property real viewportX: 0
    property real viewportY: 0
    property real viewportW: 0
    property real viewportH: 0
    property bool enableParallelLoad: true

    // ========== 新增：多级加载属性 ==========
    property real currentScale: 1.0
    property int currentLevel: 0           // 全局当前等级
    property int loadedLevel: -1           // 当前瓦片已加载的等级
    property bool inView: false            // 是否在视口内
    property var tileLevels: []            // 瓦片等级定义

    // 内部状态
    property url currentSource: ""         // 当前显示的图像源
    property bool isTransitioning: false   // 是否正在切换图像

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

    // ========== 决定是否加载 ==========
    readonly property bool shouldLoad: {
        // 不在视口内，不加载
        if (!isInViewport) {
            return false
        }
        // 启用并行加载时全部加载
        if (enableParallelLoad) {
            return true
        }
        // 否则只加载视口内的
        return isInViewport
    }

    // ========== 状态名称（用于调试）==========
    readonly property var statusNames: ["Null", "Ready", "Loading", "Error"]

    function nowString() {
        const d = new Date()
        return `${d.toLocaleTimeString()}.${("000" + d.getMilliseconds()).slice(-3)}`
    }

    // ========== 调试边框（生产环境可删除或设为不可见）==========
    Rectangle{
        anchors.fill: parent
        border.width: 1
        color: "#00000000"

        // 根据状态改变边框颜色
        border.color: {
            if (!isInViewport) return "#33000000"  // 不在视口：几乎透明
            if (loadedLevel < 0) return "#FFA500"   // 未加载：橙色
            if (loadedLevel === currentLevel) return "#00FF00"  // 已加载最新：绿色
            return "#FFFF00"  // 需要升级：黄色
        }

        // 显示瓦片信息
        Text {
            anchors.centerIn: parent
            text: {
                var txt = "[" + row_ + "," + col_ + "]"
                if (loadedLevel >= 0) {
                    txt += "\nL" + loadedLevel
                }
                return txt
            }
            color: "white"
            font.pixelSize: 14
            font.bold: true
            style: Text.Outline
            styleColor: "black"
            visible: isInViewport
        }
    }

    // ========== 主显示图像 ==========
    Image {
        id: displayImage
        anchors.fill: parent
        cache: true
        asynchronous: true
        fillMode: Image.Stretch
        source: currentSource
        opacity: 1.0

        onStatusChanged: {
            if (status === Image.Ready) {
                // 图像加载完成，记录等级
                console.log("[Tile " + row_ + "," + col_ + " " + nowString() + "] Level " + currentLevel + " loaded ✓")
            } else if (status === Image.Error) {
                console.log("[Tile " + row_ + "," + col_ + " " + nowString() + "] Level " + currentLevel + " error ✗")
            }
        }

        // 淡入动画（平滑切换）
        Behavior on opacity {
            NumberAnimation {
                duration: 150
                easing.type: Easing.InOutQuad
            }
        }
    }

    // ========== 构建图像URL ==========
    function buildImageUrl(level) {
        if (imageUrl === "" || imageUrl === undefined) {
            return ""
        }

        var url = imageUrl
        // 添加瓦片行列参数
        url += "?row=" + row_
        url += "&col=" + col_
        url += "&count=" + count_
        // 添加等级参数
        url += "&level=" + level

        return url
    }

    // ========== 更新等级（外部调用）==========
    function updateLevel(newLevel) {
        // 不在视口内，卸载图像释放内存
        if (!isInViewport) {
            if (currentSource !== "") {
                console.log("[Tile " + row_ + "," + col_ + "] Unload (out of view)")
                currentSource = ""
                loadedLevel = -1
            }
            return
        }

        // 已经是目标等级或更高，不需要升级
        if (loadedLevel >= newLevel) {
            return
        }

        // 构建新URL
        var newSource = buildImageUrl(newLevel)

        // 还没有加载过任何图像，直接加载
        if (loadedLevel < 0) {
            console.log("[Tile " + row_ + "," + col_ + "] Initial load Level " + newLevel)
            currentSource = newSource
            loadedLevel = newLevel
        } else if (newLevel > loadedLevel) {
            // 升级到更高质量
            console.log("[Tile " + row_ + "," + col_ + "] Upgrade Level " + loadedLevel + " → " + newLevel)

            // 直接切换（QML的Image组件会自动处理缓存）
            currentSource = newSource
            loadedLevel = newLevel
        }
    }

    // ========== 监听视口变化 ==========
    onIsInViewportChanged: {
        if (!isInViewport && currentSource !== "") {
            // 离开视口，卸载图像
            currentSource = ""
            loadedLevel = -1
        } else if (isInViewport && currentSource === "" && currentLevel >= 0) {
            // 进入视口，加载图像
            updateLevel(currentLevel)
        }
    }

    // ========== 组件完成时初始加载 ==========
    Component.onCompleted: {
        if (shouldLoad && currentLevel >= 0) {
            updateLevel(currentLevel)
        }
    }

    // ========== 监听全局等级变化 ==========
    onCurrentLevelChanged: {
        if (isInViewport) {
            updateLevel(currentLevel)
        }
    }
}
