import QtQuick
import QtQuick.Controls
import QtQuick.Controls.Material
import QtQuick.Layouts
import QtGraphs
import "../../Base"
import "../../Comp/Card"
CardBase {
    id:root
    Layout.fillWidth: true
    max_height:100//col.height+10
    title:  ""       //"当前卷信息"

    content_body:Item{
        id:col
        width:root.width
        Layout.fillWidth: true
        Layout.fillHeight: true
                visible: root.isShow
        Flow{
            anchors.fill: parent
            Layout.fillWidth: true
            Layout.fillHeight: true

            FlowRowItem{
                title:qsTr("缺陷数量")
                value:core.currentCoilModel["coilId"]
            }

            FlowRowItem{
                title:"卷数"
                value:core.currentCoilModel.nextInfo
            }

            FlowRowItem{
                title:"识别率 "
                value:core.currentCoilModel.coilNo
            }

            FlowRowItem{
                title:"卷识别率 "
                value:core.currentCoilModel.coilType
            }
        }
    }
}
