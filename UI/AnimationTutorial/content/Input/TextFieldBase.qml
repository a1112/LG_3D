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
            menu.popup()}
    }

    Menu{
        id:menu
        MenuItem{
            text:"复制"
            onClicked:{
                cpp.clipboard.setText(root.selectedText())
            }
        }
        MenuItem{
            text:"粘贴"
        }
        MenuItem{
            text:"清空"
        }
    }
}
