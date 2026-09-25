import QtQuick
import QtQuick.Controls
import Qt5Compat.GraphicalEffects
import "../../Base"

Item {
    id: root

    required property var surfaceData
    required property var dataShowCore
    required property var style

    anchors.fill: parent

    function appendQuery(url, query) {
        if (!url) {
            return ""
        }
        return url + (url.indexOf("?") >= 0 ? "&" : "?") + query
    }

    BackSvg{
        anchors.fill: parent
        style: root.style
    }

    // ========== 缩略图层（快速显示）==========
    Image {
        id: thumbnailImage
        anchors.fill: parent
        cache: true
        fillMode: Image.PreserveAspectFit
        asynchronous: true
        visible: source !== "" && status === Image.Ready
        opacity: fullImage.status === Image.Ready ? 0.0 : 1.0

        // 淡出动画
        Behavior on opacity {
            NumberAnimation { duration: 200 }
        }

        // 缩略图源：带有 thumbnail=true 参数（仅用于 HTTP URL）
        property string thumbnailBaseUrl: {
            if (!root.surfaceData.source
                    || !root.surfaceData.hasViewData(
                        root.surfaceData.currentViewKey)) {
                return ""
            }
            // 只有 HTTP/HTTPS URL 才添加 thumbnail 参数
            if (root.surfaceData.source.startsWith("http://")
                    || root.surfaceData.source.startsWith("https://")) {
                return root.appendQuery(root.surfaceData.source,
                                        "thumbnail=true")
            }
            return ""  // file:// 不使用缩略图，直接加载原图
        }

        source: thumbnailBaseUrl
    }

    // ========== 全图层（覆盖在缩略图上）==========
    Image {
        id: fullImage
        cache: false
        anchors.fill: parent
        fillMode: Image.PreserveAspectFit
        asynchronous: true
        source: root.surfaceData.hasViewData(root.surfaceData.currentViewKey)
                ? root.surfaceData.source : ""

        onStatusChanged: {
            if (status === Image.Ready) {
                root.dataShowCore.sourceWidth = sourceSize.width
                root.dataShowCore.sourceHeight = sourceSize.height
            }
        }

        Component.onCompleted: {
            root.dataShowCore.imageItem = fullImage
        }
    }

    // ========== Gamma 调整层 ==========
    GammaAdjust {
        anchors.fill: fullImage
        source: fullImage
        gamma: root.dataShowCore.adjustConfig.image_gamma
        enabled: visible
        visible: root.dataShowCore.adjustConfig.image_gamma_enable
    }

    // ========== 错误叠加层 ==========
    Image{
        id: image_show
        cache: false
        anchors.fill: parent
        fillMode: Image.PreserveAspectFit
        asynchronous: true
        source: root.surfaceData.error_source
        visible: root.surfaceData.error_visible
        enabled: visible
        opacity: root.surfaceData.tower_warning_show_opacity / 100
    }

    BusyIndicator {
        anchors.centerIn: parent
        running: fullImage.status === Image.Loading && thumbnailImage.status !== Image.Ready
        visible: running
        width: 36
        height: 36
    }

    Rectangle {
        anchors.centerIn: parent
        visible: fullImage.status === Image.Error
        width: imageErrorLabel.implicitWidth + 28
        height: imageErrorLabel.implicitHeight + 16
        radius: root.style.controlRadius
        color: root.style.panelElevatedColor
        border.width: 1
        border.color: root.style.statusErrorColor

        Label {
            id: imageErrorLabel
            anchors.centerIn: parent
            text: qsTr("图像加载失败")
            color: root.style.statusErrorColor
        }
    }

    Component.onCompleted: {
        root.dataShowCore.image_show = image_show
    }
}
