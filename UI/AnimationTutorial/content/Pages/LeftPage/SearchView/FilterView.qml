import QtQuick
import QtQuick.Controls
import QtQuick.Controls.Material
import QtQuick.Layouts
import "../../../Labels"
Popup {
        id: popup
        width:350
        height:400
        ColumnLayout{
                anchors.fill:parent
                spacing:5
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
                implicitHeight:40

                Item{
                    Layout.fillWidth:true
                     implicitHeight:40
                }
                Button{
                    text: "   重置   "
                    Material.background: Material.color(Material.Green)
                }
                Item{
                    implicitWidth:50
                     implicitHeight:10
                }
                Button{
                    text: "   确认   "
                    Material.background: Material.color(Material.Blue)
                }
            }


        }


}
