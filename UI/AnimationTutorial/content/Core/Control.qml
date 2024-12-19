import QtQuick
import QtQuick.Window
import "../Base"
Item {
    id:root
    property var visibility: auth.isAdmin?Window.Windowed:Window.FullScreen
    readonly property bool isFullScreen: visibility == Window.FullScreen
    readonly property bool isWindowed: visibility == Window.Windowed

    property bool lockControl: true // 锁定控制器, 使用单独控制器


    SettingsBase{
        fileName: "Control.ini"
        property alias lockControl:root.lockControl
    }
}
