import QtQuick
import QtQuick.Controls
import QtQuick.Controls.Material
import QtQuick.Layouts

Item{
    id:root
    height: 45
    Layout.fillWidth: true
    Pane{
        anchors.fill: parent
        Material.elevation: 6
    }
    RowLayout{
        anchors.fill: parent
        spacing: 10

            TabBar{

                Repeater{
                    id: list_view
                    model: ListModel{
                        ListElement{
                            label:"缺陷列表"
                        }
                    }
                    TabButton{
                        text: label
                        font.bold: true
                        onClicked: {
                            core.globalViewIndex = index
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
            text: qsTr("缺陷数据分析")
        }
        Item{
            Layout.fillWidth: true
            Layout.fillHeight: true
        }

        CheckDelegate{
            text: qsTr("显示报警类别")
             implicitHeight: root.height-5

        }
        Button{
            icon.source: "../../icons/uploading.png"
            text: qsTr("导出")
            implicitHeight: root.height-5
        }

        Button{
            icon.source: "../../icons/Flush_Dark.png"
            text: qsTr("刷新")
            implicitHeight: root.height-5
        }
        Item{
            width: 5
            Layout.fillHeight: true
        }

    }

}
