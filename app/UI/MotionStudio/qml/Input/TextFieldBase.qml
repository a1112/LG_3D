import QtQuick
import QtQuick.Controls
TextField {
    id:root
    implicitHeight:40
    selectByMouse:true
    font.family:"Microsoft YaHei"
    font.bold:true
    font.pointSize:13
    MouseArea{
        acceptedButtons:Qt.RightButton
        anchors.fill:parent
        onClicked:{
            root.selectAll()
            menu.popup()
            root.forceActiveFocus()
        }
    }

    Menu{
        id:menu
        MenuItem{
            text:"复制"
            onClicked:{
                root.copy()
                // cpp.clipboard.setText(root.selectedText())
            }
        }
        MenuItem{
            text:"粘贴"
            onClicked:{
            root.paste()
            }
        }
        MenuItem{
            text:"清空"
            onClicked:{
                root.clear()

            }
        }
    }
}
