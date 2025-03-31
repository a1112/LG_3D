import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
//  类别信息
import "../../Base"
import "../../Comp/Card"
CardBase {
    id:root
    Layout.fillWidth : true
    max_height : 200
    title :  qsTr("缺陷总计")       //"当前卷信息"

    content_body:Item{
        id : col
        width : root.width
        Layout.fillWidth : true
        Layout.fillHeight : true
        visible: root.isShow
        Flow{
            anchors.fill: parent
            Layout.fillWidth: true
            Layout.fillHeight: true

            Repeater{
                model: 10
            DefectFlowRowItem{
                title:"卷数"
                value:core.currentCoilModel.nextInfo
            }
            }
        }

    }
}
