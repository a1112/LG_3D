import QtQuick
import QtQuick.Controls
import Qt5Compat.GraphicalEffects
import "../../Base"

Item {
    id: root
    anchors.fill: parent

    function appendQuery(url, query) {
        if (!url) {
            return ""
        }
        return url + (url.indexOf("?") >= 0 ? "&" : "?") + query
    }

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
            if (!surfaceData.source || !surfaceData.hasViewData(surfaceData.currentViewKey)) return ""
            // 只有 HTTP/HTTPS URL 才添加 thumbnail 参数
            if (surfaceData.source.startsWith("http://") || surfaceData.source.startsWith("https://")) {
                return root.appendQuery(surfaceData.source, "thumbnail=true")
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
        source: surfaceData.hasViewData(surfaceData.currentViewKey) ? surfaceData.source : ""

        onStatusChanged: {
            if (status === Image.Ready) {
                dataShowCore.sourceWidth = sourceSize.width
                dataShowCore.sourceHeight = sourceSize.height
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
        cache: false
        anchors.fill: parent
        fillMode: Image.PreserveAspectFit
        asynchronous: true
        source: surfaceData.error_source
        visible: surfaceData.error_visible
        enabled: visible
        opacity: surfaceData.tower_warning_show_opacity/100
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
        radius: coreStyle.controlRadius
        color: coreStyle.panelElevatedColor
        border.width: 1
        border.color: coreStyle.statusErrorColor

        Label {
            id: imageErrorLabel
            anchors.centerIn: parent
            text: qsTr("图像加载失败")
            color: coreStyle.statusErrorColor
        }
    }

    Component.onCompleted: {
        dataShowCore.image_show = image_show
    }
}
