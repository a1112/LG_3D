import QtQuick

import QtQuick.Controls.Material
import QtQuick.Layouts
Item {
    width: 240
    height: 150
    ItemDelegate{
        anchors.fill: parent
    }

    ColumnLayout{
        Item{
            width: 240
            height: 120
            Rectangle{
                radius: 3
                anchors.fill: parent
                clip: true
                color: "#2e2e2e"
                Image{
                    anchors.centerIn: parent
                    source:"image://icon/"+filePath// "../icons/test.png"
                    fillMode: Image.PreserveAspectFit
                }

            }

        }
        RowLayout{
            Layout.fillWidth: true
            Layout.fillHeight: true
            Label{
                text: fileName
            }
            Item{
                Layout.fillWidth: true
                Layout.fillHeight: true
            }
            Row{
                height: 30
                Button{
                    height: parent.height
                    width: lab.width+20
                    Material.background: "#06967E"
                    Label{
                        id:lab
                        anchors.centerIn: parent
                        text: qsTr("安装")
                    }
                    onClicked: {
                        core.system(filePath)
                    }
                }
            }
        }
    }}
