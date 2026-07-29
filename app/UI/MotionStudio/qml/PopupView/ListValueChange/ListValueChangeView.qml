
import "../Base"
import "../../Labels"
import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
PopupBase {
    id:root
    width: adaptive.boundedWidth(850, 620, 1080)
    height: adaptive.boundedHeight(500, 380, 680)
    onOpened:{
        inputRow.init()

    }
    Item{
        width:root.width
        height: root.height - adaptive.headerSideGap
        ColumnLayout{
            anchors.fill:parent
            TitleLabel{
                Layout.alignment:Qt.AlignHCenter
                text:qsTr("列表数值变化曲线")
                color: Material.color(Material.Blue)
            }
            ViewChangeInput{
                id:inputRow

            }
            Item{
                id:list
                Layout.fillWidth:true
                Layout.fillHeight:true
                clip:true

            }

        }
    }
}
