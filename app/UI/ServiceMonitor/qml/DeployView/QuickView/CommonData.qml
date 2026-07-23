import QtQuick
import QtQuick.Controls
ScrollView {
    id:root
    width:parent.width
    height:parent.height
    contentHeight: col.height
    contentWidth: col.width
    ScrollBar.vertical: ScrollBar{
        anchors.right: parent.right
        height: parent.height
    }
    Column{
        id:col
        width: root.width
        // 1.开始
        ItemDelegateText{
            copyList:ListModel{
                ListElement{
                    value:"HKEY_LOCAL_MACHINE\SOFTWARE\Microsoft\Windows NT\CurrentVersion\Winlogon"
                }
                ListElement{
                    value:"DefaultUserName"
                }
                ListElement{
                    value:"DefaultPassword"
                }
            }
            title: "Netplwiz 无 要使用本计算机，用户必须输入用户名和密码"
        }

       }



}
