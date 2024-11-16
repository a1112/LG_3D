import QtQuick
import QtQuick.Window

Item {

    property var visibility: auth.isAdmin?Window.Windowed:Window.FullScreen
    readonly property bool isFullScreen: visibility == Window.FullScreen
    readonly property bool isWindowed: visibility == Window.Windowed

}
