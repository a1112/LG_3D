
import "../Base"
import "../../Labels"
import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
PopupBase {
    id:root
    width:500
    height:500
    Item{
        width:root.width
        height:root.height-20
        ColumnLayout{
            anchors.fill:parent
            TitleLabel{
                Layout.alignment:Qt.AlignHCenter
                text:"缺陷列表"
                color:Material.color(Material.Blue)
            }
            Item{
                Layout.fillWidth:true
                Layout.fillHeight:true
                clip:true
                ListView{
                    anchors.fill:parent
                    model:global.defectClassProperty.defectDictModel
                    delegate:DefectClassShowItem{
                    }
                }
            }
            RowLayout{
                Layout.fillWidth:true
                implicitHeight:30
                spacing:20
                Item{
                    Layout.fillWidth:true
                    implicitHeight:30
                }
                Button{
                    text:"保存 "
                }
                Button{
                    text:"添加 "
                }
            }
        }
    }
}
