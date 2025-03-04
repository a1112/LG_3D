import QtQuick
import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import QtQuick.Controls.Material

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
        }
        Item{
            implicitWidth: 5
            implicitHeight: 2
        }
    }

}
