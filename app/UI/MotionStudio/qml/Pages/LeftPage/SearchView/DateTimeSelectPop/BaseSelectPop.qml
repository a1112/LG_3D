import QtQuick
import QtQuick.Controls
import QtQuick.Window
Popup {
    dim: true
    modal: true
    // 设置父对象为 Overlay 的根元素，避免被裁剪
    parent: Window.contentItem ? Window.contentItem : Overlay.overlay
    // 确保弹窗在窗口内显示
    x: {
        if (parent && parent.width) {
            let centerX = (parent.width - width) / 2
            // 确保不超出左边界
            return Math.max(10, centerX)
        }
        return 100
    }
    y: {
        if (parent && parent.height) {
            let centerY = (parent.height - height) / 2
            // 确保不超出上边界
            return Math.max(10, centerY)
        }
        return 100
    }
    background: Rectangle{
        color: "#E0201F28"
    }

    function popup() {
        open()
    }
}
