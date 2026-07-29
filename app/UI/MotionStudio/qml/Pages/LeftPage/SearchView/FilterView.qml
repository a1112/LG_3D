import QtQuick
import QtQuick.Controls
import QtQuick.Controls.Material
import QtQuick.Layouts
import "../../../Labels"
Popup {
        id: popup
        width: adaptive.boundedWidth(350, 300, 460)
        height: adaptive.boundedHeight(400, 320, 520)
        ColumnLayout{
                anchors.fill:parent
                spacing: adaptive.headerButtonGap
            TitleLabel{
                Layout.alignment:Qt.AlignHCenter
                text: qsTr("查询条件")
                color: app.coreStyle.cardBorderColor
            }
            Item{
                Layout.fillWidth:true
                Layout.fillHeight:true



            }
            RowLayout{
                Layout.fillWidth:true
                implicitHeight: adaptive.scaleMetric(40, 34, 54)

                Item{
                    Layout.fillWidth:true
                     implicitHeight: adaptive.scaleMetric(40, 34, 54)
                }
                Button{
                    text: "   重置   "
                    Material.background: Material.color(Material.Green)
                }
                Item{
                    implicitWidth: adaptive.headerLargeGap
                     implicitHeight: adaptive.mainSpacing
                }
                Button{
                    text: "   确认   "
                    Material.background: Material.color(Material.Blue)
                }
            }


        }


}
