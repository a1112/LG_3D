import QtQuick 2.15
import QtQuick.Controls 2.15
import QtQuick.Layouts 1.15
import "../../Header"
ColumnLayout {
    id: root

    required property var modelStore
    required property var style

    height: 35
    RowLayout {
        Label{
            color: root.style.titleColor
            font.bold:true
            font.family: "Microsoft YaHei UI"
            font.pointSize: 14
            text: qsTr("卷号:")
        }
        Item{
            Layout.fillWidth: true
            height: 35
            TextField{
                id: textField
                anchors.fill: parent
                selectByMouse: true
                placeholderText : qsTr("请输入卷号")
            }
        }
        Item{
        width: 1
        height: 1
        }
        Item{
            height: 30
            width: 60
        CheckRec {
            style: root.style
            fillWidth: true
             height: 30
           text: qsTr("查询")
            onClicked: {
                root.modelStore.searchByCoilNo(textField.text)
            }
       }
        }

        Item{
        width: 15
        height: 1
        }
    }
}
