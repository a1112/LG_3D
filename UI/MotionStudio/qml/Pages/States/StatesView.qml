import QtQuick 2.15
import QtQuick.Controls 2.15
import QtQuick.Controls.Material
import LG3D
Rectangle {
    width: parent.width
    height: 200
    id:root
    y:ContCore.showState?parent.height-height:parent.height

    Button{
        anchors.horizontalCenter: parent.horizontalCenter
        anchors.bottom: parent.top
        text: ContCore.showState?"隐藏":"显示"
        onClicked: {
            ContCore.showState=!ContCore.showState
        }
    }

    ListView{
        anchors.fill: parent
        orientation:Qt.Horizontal

        model: ListModel{
        ListElement{}
        ListElement{}

        }
        delegate:
            Item{
             width: 200
             height: width
        Pane{
            anchors.centerIn: parent
            Material.elevation: 10
            height: 190
            width: 190
            anchors.verticalCenter: parent
            ItemDelegate{
                anchors.fill: parent
                    onClicked: {
                        ContCore.modelViewIndex=index

                }

            }

        }
        }

    }

    Item {
        id: __materialLibrary__
    }
}
