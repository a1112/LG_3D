import QtQuick 2.15
import QtQuick.Controls 2.15
import QtQuick.Layouts 1.15
import "../../Header"

ColumnLayout {
    height: 35
    RowLayout {
        Label{
            text: "流水号:"
        }
        Item{
            Layout.fillWidth: true
            implicitHeight: 35
            TextField{
                id:textField
                anchors.fill: parent
                selectByMouse: true
                placeholderText : "请输入流水号"
            }
        }
        Item{
            implicitWidth: 2
            implicitHeight: 1
        }
        Item{
            implicitWidth: 50
            implicitHeight: 30
        CheckRec {
            fillWidth: true
             height: 30
           text: qsTr("查询")
            onClicked: {
                coreModel.searchByCoilId(textField.text)
            }
       }
        }
        Item{
            implicitWidth: 15
            implicitHeight: 1
        }
    }
}
