import QtQuick

Item {
    id: root

    required property var settings

    property int row_: 0
    property int col_: 0
    property int count_: 3
    property string imageUrl: ""
    property string previewUrl: ""
    property string coilNo: ""

    property real viewportX: 0
    property real viewportY: 0
    property real viewportW: 0
    property real viewportH: 0
    property bool enableParallelLoad: false

    property real currentScale: 1.0
    property int currentLevel: 0
    property int loadedLevel: -1
    property int targetLevel: 0
    property url targetSource: ""
    property url previewSource: ""
    property string lastLoadedUrl: ""
    property bool debugLog: settings ? settings.showTileDebugBorders : false

    readonly property bool isInViewport: {
        var viewportRight = viewportX + viewportW
        var viewportBottom = viewportY + viewportH
        var tileRight = x + width
        var tileBottom = y + height
        return !(tileRight <= viewportX || x >= viewportRight
                 || tileBottom <= viewportY || y >= viewportBottom)
    }
    readonly property bool shouldLoad: enableParallelLoad || isInViewport
    readonly property bool targetReady: targetImage.status === Image.Ready

    function debugLogMessage(message) {
        if (debugLog) {
            console.log(message)
        }
    }

    function appendQuery(url, query) {
        if (!url) {
            return ""
        }
        return url + (url.indexOf("?") >= 0 ? "&" : "?") + query
    }

    function buildImageUrl(level) {
        if (!imageUrl) {
            return ""
        }
        return appendQuery(imageUrl,
                           "row=" + row_
                           + "&col=" + col_
                           + "&count=" + count_
                           + "&level=" + level)
    }

    function resetSources() {
        targetSource = ""
        previewSource = ""
        loadedLevel = -1
    }

    function unloadHighResolution() {
        if (!enableParallelLoad && targetLevel >= 2) {
            targetSource = ""
            loadedLevel = -1
        }
    }

    function loadPreview() {
        if (!settings || !settings.enable1024CacheMode) {
            return
        }
        previewSource = previewUrl ? previewUrl : appendQuery(imageUrl, "row=-2")
    }

    function updateLevel(newLevel) {
        targetLevel = Math.max(0, Math.min(4, Number(newLevel) || 0))
        if (!imageUrl || !shouldLoad) {
            unloadHighResolution()
            return
        }

        var urlChanged = lastLoadedUrl !== imageUrl
        var nextSource = buildImageUrl(targetLevel)
        if (urlChanged) {
            lastLoadedUrl = imageUrl
            resetSources()
            loadPreview()
        }
        if (targetSource !== nextSource) {
            loadedLevel = -1
            targetSource = nextSource
            debugLogMessage("[Tile " + row_ + "," + col_
                            + "] CoilNo:" + coilNo
                            + " Loading L" + targetLevel)
        }
    }

    Rectangle {
        anchors.fill: parent
        color: "#070B0F"
    }

    Image {
        id: previewImage
        anchors.fill: parent
        asynchronous: true
        cache: false
        fillMode: Image.Stretch
        source: root.previewSource
        visible: source !== "" && status === Image.Ready && !root.targetReady
    }

    Image {
        id: targetImage
        anchors.fill: parent
        asynchronous: true
        cache: false
        fillMode: Image.Stretch
        source: root.targetSource
        visible: source !== "" && status === Image.Ready
        opacity: visible ? 1 : 0

        Behavior on opacity {
            NumberAnimation { duration: 120 }
        }

        onStatusChanged: function(status) {
            if (status === Image.Ready) {
                root.loadedLevel = root.targetLevel
            } else if (status === Image.Error) {
                root.loadedLevel = -1
                root.debugLogMessage("[Tile " + root.row_ + "," + root.col_
                                     + "] failed L" + root.targetLevel)
            }
        }
    }

    Rectangle {
        anchors.fill: parent
        border.width: 1
        color: "transparent"
        z: 10
        visible: root.debugLog
        border.color: !root.isInViewport ? "#334155"
                                         : root.loadedLevel < 0 ? "#F59E0B"
                                                                : "#22C55E"

        Text {
            anchors.centerIn: parent
            text: "[" + root.row_ + "," + root.col_ + "]"
                  + (root.coilNo ? "\n" + root.coilNo : "")
                  + (root.loadedLevel >= 0 ? "\nL" + root.loadedLevel : "")
            color: "white"
            font.pixelSize: 10
            font.bold: true
            style: Text.Outline
            styleColor: "black"
            visible: root.isInViewport && parent.width > 150
        }
    }

    Component.onCompleted: {
        lastLoadedUrl = imageUrl
        loadPreview()
        updateLevel(currentLevel)
    }

    onCurrentLevelChanged: updateLevel(currentLevel)

    onShouldLoadChanged: {
        if (shouldLoad) {
            updateLevel(currentLevel)
        } else {
            unloadHighResolution()
        }
    }

    onImageUrlChanged: {
        lastLoadedUrl = ""
        resetSources()
        loadPreview()
        updateLevel(currentLevel)
    }

    onPreviewUrlChanged: {
        if (settings && settings.enable1024CacheMode) {
            loadPreview()
        }
    }
}
