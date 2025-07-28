import QtQuick 2.15
import QtQuick.Controls
import QtQuick.Controls.Material
import QtQuick.Layouts
import QtQuick.Dialogs
import "QuickView"
Item {
            anchors.fill: parent
    SplitView{
        anchors.fill: parent
        Item{
            SplitView.fillHeight: true
            SplitView.preferredWidth: 80
            id: leftPane
            ColumnLayout{
                anchors.fill: parent
                Item{
                    Layout.fillWidth: true
                    Layout.fillHeight: true
                    clip: true
                ListView{
                    id:list
                    anchors.fill: parent
                    model: ListModel{
                        ListElement{
                            title:"快捷设置"
                        }
                        ListElement{
                            title:"常用值"
                        }
                        ListElement{
                             title:"3.0部署"
                        }
                        ListElement{
                             title:"4.0部署"
                        }
                    }
                    highlight: Rectangle{
                        color: "#96067E"
                        radius: 5
                        width: parent.width-5
                        border.color: "lightblue"
                    }
                    delegate: ItemDelegate{
                        text: title
                        width:leftPane.width
                        font.bold: true
                        onClicked: {
                            list.currentIndex = index
                        }
                    }
                }
                }
            }
        }
        StackLayout{
            SplitView.fillHeight: true
            SplitView.fillWidth: true
            id: rightPane
            currentIndex: list.currentIndex
            QuickPageView{
            }
            CommonData{

            }

        }

    }
}
