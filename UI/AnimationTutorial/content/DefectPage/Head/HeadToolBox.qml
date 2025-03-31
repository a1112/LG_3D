import QtQuick
import QtQuick.Controls
import QtQuick.Controls.Material
import QtQuick.Layouts

Item{
    height: 30
    Layout.fillWidth: true
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
                            label:"缺陷列表"
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
