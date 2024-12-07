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
                value:core.currentCoilModel["coilId"]
                valueColor:Material.color(Material.Green)
            }
            FlowRowItem{
                title:"去向"
                value:core.currentCoilModel.nextInfo
            }
            // FlowRowItem{
            //     title:"卷号 "
            //     value:core.currentCoilModel.coilNo
            // }
            FlowRowItem{
                title:"钢种 "
                value:core.currentCoilModel.coilType
            }
            FlowRowItem{
                title:"外径 "
                value:core.currentCoilModel.coilDia
            }
            FlowRowItem{
                title:"内径 "
                value:core.currentCoilModel.coilInside
            }
            FlowRowItem{
                title:"卷宽 "
                value:core.currentCoilModel.coilWidth
            }
            FlowRowItem{
                title:"卷厚 "
                value:core.currentCoilModel.coilThickness
            }
            FlowRowItem{
                title:"日期 "
                value:core.currentCoilModel.coilDetectionTime.dataString
            }
            FlowRowItem{
                title:"时间 "
                value:core.currentCoilModel.coilDetectionTime.timeString
            }
        }
    }
