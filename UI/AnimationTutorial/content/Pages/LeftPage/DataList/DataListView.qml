import QtQuick 2.15
import QtQuick.Controls
import QtQuick.Layouts
import QtQuick.Controls.Material

import "../../../animation"
Item{
    id:root

    ColumnLayout {
        anchors.fill: parent
        HeadView{
        }
        Item {
            Layout.fillWidth: true
            implicitHeight: 25
            // anchors.verticalCenter: parent.verticalCenter
            Rectangle{
                anchors.fill: parent
                color: Material.color(Material.Blue)
                opacity: 0.1
            }
            RowLayout{
                anchors.fill: parent
                Rectangle{
                    implicitWidth: 2
                    implicitHeight: 1
                }

                ColumnLayout{
                    spacing: 0
                    Layout.fillWidth: true
                    implicitHeight: 30
                    RowLayout{
                        Label{
                            font.pointSize: 13
                            font.family: "Microsoft YaHei"
                            font.bold: true
                            text: "  Id "
                        }
                        Item {
                            Layout.fillWidth: true
                            implicitHeight: 1
                        }
                        Label{
                            text:"   卷号"
                            font.pointSize: 13
                            font.bold: true
                            font.family: "Microsoft YaHei"
                        }
                        Item {
                            Layout.fillWidth: true
                            implicitHeight: 1
                        }
                        Label{
                            font.pointSize: 13
                            font.bold: true

                            text: "   钢种"
                            font.family: "Microsoft YaHei"
                        }
                        Item {
                            Layout.fillWidth: true
                            implicitHeight: 1
                        }
                        Label{
                            font.pointSize: 13
                            font.bold: true
                            font.family: "Microsoft YaHei"
                            text: " 状态"
                        }
                    }
                    // RowLayout{
                    //     Layout.fillWidth: true
                    //     Label{
                    //         font.pointSize: 10
                    //         font.bold: true
                    //         color: "#747474"
                    //         text: "外："+CoilDia
                    //     }

                    //     Label{
                    //         font.pointSize: 10
                    //         font.bold: true
                    //         color: "#747474"
                    //         text: "宽："+Width
                    //     }

                    //     Label{
                    //         font.pointSize: 10
                    //         font.bold: true
                    //         color: "#747474"
                    //         text: "厚："+Thickness
                    //     }
                    // }
                    // TimeLabel{

                    // }
                }
                Item{
                    implicitWidth: 5
                    implicitHeight: 2
                }
            }

        }

        Item{
            clip: true
            Layout.fillWidth: true
            Layout.fillHeight: true
            AnimListView{
                id: listView
                anchors.fill: parent
                currentIndex: core.coilIndex
                onCurrentIndexChanged: {
                    core.setCoilIndex(currentIndex)
                }
                spacing:5
                model: coreModel.currentCoilListModel
                highlight: Rectangle {
                    color: "lightsteelblue"
                    radius: 5
                    border.color: "steelblue"
                    border.width: 3
                }
                ScrollBar.vertical: ScrollBar {
                }
                delegate:DataListViewIten{    //    -----------------------------
                    width: listView.width
                }
            }
        }
    }
    Rectangle{
        id:mask
        anchors.fill: parent
        color: "#00000000"

        border.width: 1
        border.color: Material.color(Material.Blue)
    }
    HoverHandler{
        onPointChanged: {
            leftCore.hoverPoint = Qt.point(point.position.x,point.position.y+100) // point.position
        }
        onHoveredChanged: {
            if(hovered){
                leftCore.isHoved = true
            }
            else{
                leftCore.isHoved=false
            }
        }
    }
}
