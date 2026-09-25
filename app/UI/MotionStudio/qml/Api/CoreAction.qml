import QtQuick
import QtQuick.Controls
import QtQuick.Window
Item {
    id: root

    required property var appWindow

    Action{//F11 全屏
        shortcut: StandardKey.FullScreen
        onTriggered:
            root.appWindow.visibility = root.appWindow.visibility === Window.FullScreen
                                      ? Window.Windowed : Window.FullScreen
    }
    Action{// Ctrl + C  复制
        shortcut: StandardKey.Copy
        onTriggered: {
            console.log("复制")
            //  将图像复制到剪切板
        }
    }
    Action{
        shortcut: StandardKey.Save
        onTriggered: {
            console.log("保存")
            // 保存图像
        }

    }
}
