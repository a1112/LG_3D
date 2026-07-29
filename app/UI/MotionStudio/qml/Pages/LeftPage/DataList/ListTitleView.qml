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
        color: coreStyle.headerBackgroundColor
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
                    font.bold: true
                    text: "  Id "
                }
                Item {
                    Layout.fillWidth: true
                    implicitHeight: 1
                }
                Label{
                    text:"   卷号"
                    font.bold: true
                }
                Item {
                    Layout.fillWidth: true
                    implicitHeight: 1
                }
                Label{
                    font.bold: true

                    text: "   钢种"
                }
                Item {
                    Layout.fillWidth: true
                    implicitHeight: 1
                }
                Label{
                    font.bold: true
                    text: " 缺陷/最严重"
                }
            }
        }
        Item{
            implicitWidth: 5
            implicitHeight: 2
        }
    }

}
