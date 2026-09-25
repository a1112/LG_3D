import QtQuick
import QtQuick.Window
import "../Base"
Item {
    id:root
    required property var authManager
    property var visibility: root.authManager.isAdmin
                             ? Window.Windowed : Window.FullScreen
    readonly property bool isFullScreen: visibility === Window.FullScreen
    readonly property bool isMaximized: visibility === Window.Maximized
    readonly property bool isWindowed: visibility === Window.Windowed

    property bool lockControl: true // 锁定控制器, 使用单独控制器


    SettingsBase{
        location: "Control.ini"
        property alias lockControl:root.lockControl
    }

}
