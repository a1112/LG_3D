import QtQuick
import QtQuick.Layouts
import QtQuick.Controls.Material
import "../Base"
import "../../Labels"
PopupBase {
    width:300

    height:700
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
            Item{
                Layout.fillWidth:true
                Layout.fillHeight:true
            }
            Button{
                text:"添加 "
            }
        }

    }
}
