import QtQuick
import QtQuick.Controls
import QtQuick.Controls.Material
import QtQuick.Layouts
import "../../../Labels"
Popup {
        id: root

        required property var adaptiveMetrics
        required property var style

        width: root.adaptiveMetrics.boundedWidth(350, 300, 460)
        height: root.adaptiveMetrics.boundedHeight(400, 320, 520)
        ColumnLayout{
        anchors.fill:parent
                spacing: root.style.headerButtonGap
            TitleLabel{
                Layout.alignment:Qt.AlignHCenter
                text: qsTr("查询条件")
                color: root.style.cardBorderColor
            }
            Item{
                Layout.fillWidth:true
                Layout.fillHeight:true



            }
            RowLayout{
                Layout.fillWidth:true
                implicitHeight: root.adaptiveMetrics.scaleMetric(40, 34, 54)

                Item{
                    Layout.fillWidth:true
                     implicitHeight: root.adaptiveMetrics.scaleMetric(40, 34, 54)
                }
                Button{
                    text: "   重置   "
                    Material.background: Material.color(Material.Green)
                }
                Item{
                    implicitWidth: root.adaptiveMetrics.headerLargeGap
                     implicitHeight: root.adaptiveMetrics.mainSpacing
                }
                Button{
                    text: "   确认   "
                    Material.background: Material.color(Material.Blue)
                }
            }


        }


}
