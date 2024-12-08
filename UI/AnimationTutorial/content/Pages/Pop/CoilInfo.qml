import QtQuick 2.15
import QtQuick.Controls
import QtQuick.Controls.Material
import QtQuick.Layouts
import "../../Base"
import "../../Comp/Card"
import "../../btns"

Item {
    id:root
    width:root.width
    Layout.fillWidth: true
    Layout.fillHeight: true
        Flow{
            anchors.fill: parent
            FlowRowItem{
                title:"流水号"
                value:coilModel.coilId
                valueColor:Material.color(Material.Green)
            }
            FlowRowItem{
                title:"去向"
                value:coilModel.nextInfo
            }
            // FlowRowItem{
            //     title:"卷号 "
            //     value:core.currentCoilModel.coilNo
            // }
            FlowRowItem{
                title:"钢种 "
                value:coilModel.coilType
            }
            FlowRowItem{
                title:"外径 "
                value:coilModel.coilDia
            }
            FlowRowItem{
                title:"内径 "
                value:coilModel.coilInside
            }
            FlowRowItem{
                title:"卷宽 "
                value:coilModel.coilWidth
            }
            FlowRowItem{
                title:"卷厚 "
                value:coilModel.coilThickness
            }
            FlowRowItem{
                title:"日期 "
                value:coilModel.coilDetectionTime.dataString
            }
            FlowRowItem{
                title:"时间 "
                value:coilModel.coilDetectionTime.timeString
            }
        }
    }
