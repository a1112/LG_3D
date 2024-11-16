import QtQuick 2.15
import QtQuick.Controls 2.15
import QtQuick.Controls.Material
import QtQuick.Layouts

Item{
    height: 35
    width: 1920
    Pane{
        anchors.fill: parent
        Material.elevation: 6
    }
    RowLayout{
        anchors.fill: parent
    Row{
        y:-4
        TabBar{
            height: 35
            Repeater{
                id: list_view
                model: ListModel{
                    ListElement{
                        label:"实时"
                    }
                    ListElement{
                        label:"报警查看"
                    }
                    ListElement{
                        label:"历史"
                    }
                    ListElement{
                        label:"样本管理"
                    }
                }

                TabButton{
                    text: label
                    height: 35
                    width: 100
                    font.bold: true

                    onClicked: {
                        core.globalViewIndex = index
                    }
                }
            }
        }
    }

    Item{
        Layout.fillWidth: true
        Layout.fillHeight: true
    }

    TitleText{
        font.pixelSize: 20
    }
    Item{
        Layout.fillWidth: true
        Layout.fillHeight: true
    }
    }

    }
