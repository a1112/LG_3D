import QtQuick
import QtQuick.Controls.Material

ItemDelegate {
    height: 40
    width: col.width
    property alias title: text_id.text
    property string cmd: ""
    property ListModel copyList: ListModel{

    }

    Menu{
        id: menu
            Repeater{
                model: copyList

                MenuItem {
                    text: "复制"+value
                    onTriggered: {
                        core.setText(value)
                    }

                }

            }



    }
    Rectangle{
        width: parent.width
        height: 2
        anchors.bottom: parent.bottom
    }
    LabelBase {
        id: text_id
        text: "账户设置 - 修改账户密码"
    }
    onClicked: {
        core.system(cmd)
    }
    MouseArea{
        anchors.fill: parent
        acceptedButtons: Qt.RightButton
        onClicked: {
            menu.popup()
        }
    }
}
