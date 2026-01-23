import QtQuick
import Qt5Compat.GraphicalEffects
import "../../Base"

Item {
    anchors.fill: parent

    BackSvg{
        anchors.fill: parent
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
            if (!surfaceData.source) return ""
            // 只有 HTTP/HTTPS URL 才添加 thumbnail 参数
            if (surfaceData.source.startsWith("http://") || surfaceData.source.startsWith("https://")) {
                return surfaceData.source + "&thumbnail=true"
            }
            return ""  // file:// 不使用缩略图，直接加载原图
        }

        // 监听源变化，加载缩略图
        onThumbnailBaseUrlChanged: {
            if (thumbnailBaseUrl !== "") {
                source = thumbnailBaseUrl
            }
        }
    }

    // ========== 全图层（覆盖在缩略图上）==========
    Image {
        id: fullImage
        cache: true
        anchors.fill: parent
        fillMode: Image.PreserveAspectFit
        asynchronous: true
        source: surfaceData.source

        onStatusChanged: {
            if (status === Image.Ready) {
                dataShowCore.sourceWidth = sourceSize.width
                dataShowCore.sourceHeight = sourceSize.height
                // 全图加载完成后，缩略图淡出
                thumbnailImage.opacity = 0.0
            }
        }

        Component.onCompleted: {
            dataShowCore.imageItem = this
        }
    }

    // ========== Gamma 调整层 ==========
    GammaAdjust {
        anchors.fill: fullImage
        source: fullImage
        gamma: dataShowCore.adjustConfig.image_gamma
        enabled: visible
        visible: dataShowCore.adjustConfig.image_gamma_enable
    }

    // ========== 错误叠加层 ==========
    Image{
        id: image_show
        cache: true
        anchors.fill: parent
        fillMode: Image.PreserveAspectFit
        asynchronous: true
        source: surfaceData.error_source
        visible: surfaceData.error_visible && dataShowCore.adjustConfig.image_gamma_enable
        enabled: visible
        opacity: surfaceData.tower_warning_show_opacity/100
    }

    Component.onCompleted: {
        dataShowCore.image_show = image_show
    }
}
