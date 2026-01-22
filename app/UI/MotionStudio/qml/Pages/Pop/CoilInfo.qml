import QtQuick
import QtQuick.Controls
import QtQuick.Controls.Material
import QtQuick.Layouts
import "../../Base"
import "../../Comp/Card"
import "../../btns"

Item {
    id:root
    width:root.width
    property var coilModel
    visible: coilModel !== undefined && coilModel.coilId !== undefined
        Flow{
            anchors.fill: parent
            FlowRowItem{
                title:"流水号"
                value:coilModel ? coilModel.coilId || "" : ""
                valueColor:Material.color(Material.Green)
            }
            FlowRowItem{
                title:"去向"
                value:coilModel ? coilModel.nextInfo || "" : ""
            }
            // FlowRowItem{
            //     title:"卷号 "
            //     value:core.currentCoilModel.coilNo
            // }
            FlowRowItem{
                title:"钢种 "
                value:coilModel ? coilModel.coilType || "" : ""
            }
            FlowRowItem{
                title:"外径 "
                value:coilModel ? coilModel.coilDia || "" : ""
            }
            FlowRowItem{
                title:"内径 "
                value:coilModel ? coilModel.coilInside || "" : ""
            }
            FlowRowItem{
                title:"卷宽 "
                value:coilModel ? coilModel.coilWidth || "" : ""
            }
            FlowRowItem{
                title:"卷厚 "
                value:coilModel ? coilModel.coilThickness || "" : ""
            }
            FlowRowItem{
                title:"日期 "
                value:coilModel && coilModel.coilCreateTime ? coilModel.coilCreateTime.dataString || "" : ""
            }
            FlowRowItem{
                title:"时间 "
                value:coilModel && coilModel.coilCreateTime ? coilModel.coilCreateTime.timeString || "" : ""
            }
        }
    }
