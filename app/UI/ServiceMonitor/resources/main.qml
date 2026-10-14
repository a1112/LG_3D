import Qt.labs.settings 1.1
import QtQuick
import QtQuick.Window
import QtQuick.Controls
import QtQuick.Controls.Material
import "qml"

ApplicationWindow {
    property int startupRequestedVisibility: Window.Windowed
    property QtObject startupGeometry: QtObject {
        property var saved: Settings {
            fileName: typeof startupGeometrySettingsFile === "undefined" ? "" : startupGeometrySettingsFile
            category: "StartupWindowGeometry"
            property int savedX: 0
            property int savedY: 0
            property int savedWidth: 0
            property int savedHeight: 0
        }
        property bool ready: false
        function remember() {
            if (!ready || window.visibility !== Window.Windowed) return
            saved.savedX = window.x; saved.savedY = window.y
            saved.savedWidth = window.width; saved.savedHeight = window.height
        }
        property var initialize: Timer {
            interval: 0; running: true; repeat: false
            onTriggered: {
                const restored = startupGeometry.saved.savedWidth > 0 && startupGeometry.saved.savedHeight > 0
                let screen = window.screen
                if (restored) {
                    const screens = Qt.application.screens
                    for (let i = 0; i < screens.length; ++i) {
                        const candidate = screens[i]
                        if (startupGeometry.saved.savedX >= candidate.virtualX && startupGeometry.saved.savedX < candidate.virtualX + candidate.width && startupGeometry.saved.savedY >= candidate.virtualY && startupGeometry.saved.savedY < candidate.virtualY + candidate.height) { screen = candidate; break }
                    }
                    window.screen = screen
                }
                let area = {x: screen.virtualX, y: screen.virtualY + 32, width: Math.min(screen.width, screen.desktopAvailableWidth), height: Math.min(screen.height, screen.desktopAvailableHeight) - 64}
                if (typeof startupWorkAreas !== "undefined") {
                    for (let i = 0; i < startupWorkAreas.length; ++i) {
                        if (startupWorkAreas[i].screenX === screen.virtualX && startupWorkAreas[i].screenY === screen.virtualY) { area = startupWorkAreas[i]; break }
                    }
                }
                const aw = area.width, ah = area.height
                const maxW = Math.max(1, aw - 64), maxH = Math.max(1, ah - 96)
                const nominalMinimumW = Math.min(680, maxW)
                const nominalMinimumH = Math.min(440, maxH)
                const width = restored ? startupGeometry.saved.savedWidth : Math.min(920, aw * 0.82)
                const height = restored ? startupGeometry.saved.savedHeight : Math.min(620, ah * 0.84)
                const sx = area.x, sy = area.y
                const frame = typeof startupWindowFrame === "undefined" ? {left:0, top:0, right:0, bottom:0} : startupWindowFrame
                const rawW = Math.max(1, aw - frame.left - frame.right)
                const rawH = Math.max(1, ah - frame.top - frame.bottom)
                const fittedW = restored && width <= rawW ? width : Math.min(width, maxW)
                const fittedH = restored && height <= rawH ? height : Math.min(height, maxH)
                window.minimumWidth = Math.min(nominalMinimumW, restored ? fittedW : maxW)
                window.minimumHeight = Math.min(nominalMinimumH, restored ? fittedH : maxH)
                window.width = Math.max(window.minimumWidth, fittedW)
                window.height = Math.max(window.minimumHeight, fittedH)
                window.x = restored ? Math.max(sx + frame.left, Math.min(startupGeometry.saved.savedX, sx + aw - window.width - frame.right)) : sx + (aw - window.width + frame.left - frame.right) / 2
                window.y = restored ? Math.max(sy + frame.top, Math.min(startupGeometry.saved.savedY, sy + ah - window.height - frame.bottom)) : sy + (ah - window.height + frame.top - frame.bottom) / 2
                window.visibility = window.startupRequestedVisibility
                startupGeometry.ready = true
            }
        }
        property var changes: Connections {
            target: window
            function onStartupRequestedVisibilityChanged() {
                if (startupGeometry.ready) window.visibility = window.startupRequestedVisibility
            }
            function onXChanged() { startupGeometry.remember() }
            function onYChanged() { startupGeometry.remember() }
            function onWidthChanged() { startupGeometry.remember() }
            function onHeightChanged() { startupGeometry.remember() }
            function onClosing() { startupGeometry.remember() }
        }
    }

    id:window
    width: 920
    height: 620
    visibility: Window.Hidden

    property bool isDark: true

    Material.theme: isDark?Material.Dark:Material.Light
    title: qsTr("管理平台")
    MainLayout{
    }

}
