import QtQuick
import QtQuick.Controls
import QtQuick.Controls.Material

Popup {
    id: root

    // 保持与原 Menu 用法兼容
    function popup() { open() }

    DragHandler { }

    background: Pane {
        Material.elevation: 25
    }
}
