import QtQuick
import QtQuick.Window
import QtQuick.Controls
import QtQuick.Controls.Material
import "qml"

ApplicationWindow {
    id:window
    width:Math.max(1000,Screen.width/3)
    height: Math.max(500,Screen.height/2.5)
    visible: true

    property bool isDark: true

    Material.theme: isDark?Material.Dark:Material.Light
    title: qsTr("管理平台")
    MainLayout{
    }

}
